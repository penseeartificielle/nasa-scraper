# -*- coding: utf-8 -*-
"""
Created on Mon Mar 19 10:30:33 2018

@author: Lambert Rosique
"""

# Installer Python 3
# pip3 install spyder
# pip3 install bs4
# pip3 install requests

import requests
import shutil
from bs4 import BeautifulSoup
from dateutil.parser import parse
import datetime
import os.path
import sys, getopt
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import configparser
import threading
import duplicateremover as dr
import threadsutils as tu

IFRAME_IGNORE = ['youtube','vimeo']

# Cette fonction vérifie si date début <= date <= date fin
def date_in_range(date, dd, df):
    if date != '' and date is not None:
        date = parse(date, yearfirst=True)
        if dd is not None:
            dd = parse(dd, yearfirst=True)
            if dd > date:
                return False
        if df is not None:
            df = parse(df, yearfirst=True)
            if df < date:
                return False
    return True
  
def str_contains(strli, sentence):
    for s in strli:
        if s in sentence:
            return True
    return False

# Récupère le lien pour aller sur chaque article (compris entre les dates demandées)      
def get_liens_articles(archive_photos):
    global date_debut_batch
    global date_fin_batch
    liste_articles = []
    for link in archive_photos.find_all('a'):
        if link is not None and link.get('href') is not None:
            link = link.get('href')
            if link.startswith('ap'):
                date = link.replace('ap','').replace('.html','')
                if date_in_range(date, date_debut_batch, date_fin_batch):
                    liste_articles.append('https://apod.nasa.gov/apod/'+link)
    return liste_articles

# Récupère la liste des : lien pour télécharger l'image, le nom de l'image, et la date de l'image
def get_liens_images(liste_articles, session, result, index):
    liste_images = []
    liste_refus = []   
    for lien in liste_articles:
        nom, lien_img, date = get_lien_image(lien, session)
        if lien_img is not None:
            liste_images.append((nom, lien_img, date))
        else:
            liste_refus.append(lien)
    result[index] = (liste_images, liste_refus)

def threading_liens_images(nb_threads, articles, session):
    articles = tu.decouper_liste_threads(liste_articles, nb_threads)
    
    threads = [None]*nb_threads
    results = [None]*nb_threads
    for i in range(len(threads)):
        threads[i] = threading.Thread(target=get_liens_images, args=(articles[i], session, results, i))
        threads[i].start()
    
    liste_images = []
    liste_refus = []  
    for i in range(len(threads)):
        threads[i].join()
        liste_images += results[i][0]
        liste_refus += results[i][1] 
    return liste_images, liste_refus

# Récupère 1 triplet d'informations à partir de l'url de l'article
def get_iframe(lien, session):
    l = session.get(lien).text
    souplien = BeautifulSoup(l, 'html.parser')
    lien_iframe = souplien.find('iframe')
    if lien_iframe is not None:
        lien_iframe = lien_iframe.get('src')
        if str_contains(IFRAME_IGNORE, lien_iframe):
            lien_iframe = None
    return lien_iframe

def get_image_from_iframe(lien_iframe, session):
    if lien_iframe is not None:
        l = session.get(lien_iframe).text
        souplien = BeautifulSoup(l, 'html.parser')
        lien_img = souplien.find('img')
        nom = ''
        if lien_img is not None:
            lien_img = lien_img.get('src')
            if lien_img is not None:
                lien_iframe = "/".join(lien_iframe.split('/')[:-1])
                nom = lien_img
                lien_img = lien_iframe+"/"+lien_img
            else:
                lien_img = None
        return nom, lien_img

def get_lien_image(lien, session):
    l = session.get(lien).text
    souplien = BeautifulSoup(l, 'html.parser')
    liste_lien_img = souplien.findAll('a')
    nom = ''
    date = lien.split('/')[-1:][0].replace('ap','').replace('.html','')
    img_trouvee = False
    for li in liste_lien_img:
        lien_img = li.get('href')
        if lien_img is not None and lien_img.startswith('image'):
            lien_img = 'https://apod.nasa.gov/apod/'+lien_img
            nom = lien_img.split('/')[-1:][0]
            img_trouvee = True
            break
    if not img_trouvee:
        lien_img = None
        lien_iframe = get_iframe(lien, session)
        if lien_iframe is not None:
            nom, lien_img = get_image_from_iframe(lien_iframe, session)
    return nom, lien_img, date

# Télécharge toutes les images de la liste
def telecharger_images(liste_images, session, result, index):
    liste_fail = []
    if liste_images != []:
        total_images = len(liste_images)
        cpt = 0
        for nom,lien,date in liste_images:
            cpt += 1
            telecharger_image(nom,lien,date, cpt, total_images, session, liste_fail, index)
    result[index] = liste_fail

# Télécharge une image
def telecharger_image(nom,lien,date, cpt, total_images, session, liste_fail, index):
    try:
        r = session.get(lien, stream=True)
        if r.status_code == 200:
            with open(os.path.join(save_folder, date+"_"+nom), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                print("   Tuyère "+str(index)+" ("+str(cpt)+"/"+str(total_images)+") Téléportation de l'IA "+date+"_"+nom+" confirmée.")
                print("      Source du transfert : "+lien)
        else:
            raise Exception("Code retour différent de 200")
    except Exception:
        print('   ('+str(cpt)+"/"+str(total_images)+') IA '+date+"_"+nom+" corrompue.")
        print("      Abandon du transfert : "+lien)
        liste_fail.append((date+"_"+nom, lien))
        
def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False
    
# Récupération des arguments de la ligne de commande
def recuperer_arguments(argv):
    global date_debut_batch
    global date_fin_batch
    global save_folder
    global maj
    try:
        opts, args = getopt.getopt(argv,"hmd:f:s",["datedebut=","datefin=","savedir="])
    except getopt.GetoptError:
        print('nasa-scraper.py -d <datedebut> -f <datefin> -s <savedir> -m')
        print('-d, -f and -s overrides config.ini')
        print("Add -m to automatically save your config at the end (datedebut = previous datefin, datefin = None), so you can reexecute batch over days without changing anything. If you don't add it, the question to save conf will be answered at the end.")
        print('-d and -f are of format : YYMMDD or None, same goes for config.ini')
        print('-s is relative or absolute path')
        print('A log file is automatically generated in this folder')
        print('All arguments are optional, and -m does not take value')
        print('Examples :')
        print('python nasa-scraper.py -d "180101" -m')
        print('python nasa-scraper.py -d "180101" -f "180131" -s "./january-images"')
        print('python nasa-scraper.py -m')
        print('python nasa-scraper.py')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('nasa-scraper.py -d <datedebut> -f <datefin> -s <savedir> -m')
            print('-d, -f and -s overrides config.ini')
            print("Add -m to automatically save your config at the end (datedebut = previous datefin, datefin = None), so you can reexecute batch over days without changing anything. If you don't add it, the question to save conf will be answered at the end.")
            print('-d and -f are of format : YYMMDD or None, same goes for config.ini')
            print('-s is relative or absolute path')
            print('A log file is automatically generated in this folder')
            print('All arguments are optional, and -m does not take value')
            print('Examples :')
            print('nasa-scraper.py -d "180101" -m')
            print('nasa-scraper.py -d "180101" -f "180131" -s "./january-images"')
            print('python nasa-scraper.py -m')
            print('python nasa-scraper.py')
            sys.exit()
        elif opt in ("-d", "--datedebut"):
            date_debut_batch = arg
            if date_debut_batch is not None and date_debut_batch == '':
                date_debut_batch = None
        elif opt in ("-f", "--datefin"):
            date_fin_batch = arg
            if date_fin_batch is not None and date_fin_batch == '':
                date_fin_batch = None
        elif opt in ("-s", "--savedir"):
            save_folder = arg
        elif opt in ("-m"):
            maj = True

def init_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
 
def chargement_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    date_debut_batch = None
    date_fin_batch = None
    nb_threads = None
    save_dir = './images'
    if 'DEFAULT' in config:
        if 'nb_threads' in config['DEFAULT']:
            nb_threads = config['DEFAULT']['nb_threads']
            if nb_threads is None or not isInt(nb_threads) or int(nb_threads) < 1:
                nb_threads = 1
            else:
                nb_threads = int(nb_threads)
        if 'date_debut_batch' in config['DEFAULT']:
            date_debut_batch = config['DEFAULT']['date_debut_batch']
            if date_debut_batch == '' or date_debut_batch == 'None':
                date_debut_batch = None
        if 'date_fin_batch' in config['DEFAULT']:
            date_fin_batch = config['DEFAULT']['date_fin_batch']
            if date_fin_batch == '' or date_fin_batch == 'None':
                date_fin_batch = None
        if 'save_dir' in config['DEFAULT']:
            save_dir = config['DEFAULT']['save_dir']
            assert save_dir is not None
            assert save_dir != ''
    return config, date_debut_batch, date_fin_batch, save_dir, nb_threads

def sauver_config(config, date_fin_batch):
    now = datetime.datetime.now()
    if date_fin_batch is not None:
        config["DEFAULT"]['date_debut_batch'] = date_fin_batch
    else:
        config["DEFAULT"]['date_debut_batch'] = now.strftime("%Y%m%d")[2:]
    config["DEFAULT"]['date_fin_batch'] = 'None'
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def sauvegarder_log(date_debut_batch, date_fin_batch, liste_articles, liste_images, liste_refus, liste_fail, liste_suppression):
    with open('batch_'+str(date_debut_batch)+"_"+str(date_fin_batch)+'.log', 'a') as logs:
        logs.write("[Batch du "+str(date_debut_batch)+" au "+str(date_fin_batch)+"]\n["+str(len(liste_articles))+" images détectées]\n")
        logs.write("\n[Images traitées : "+str(len(liste_images))+"]\n")
        for item in liste_images:
            logs.write("%s\n" % (str(item[2])+"_"+str(item[0])))
        logs.write("\n[Images refusées : "+str(len(liste_refus))+"]\n")
        for item in liste_refus:
            logs.write("%s\n" % str(item))
        logs.write("\n[Images échouées : "+str(len(liste_fail))+"]\n")
        for item in liste_fail:
            logs.write("%s\n" % (str(item[0])+" - "+str(item[1])))
        logs.write("\n[Images supprimées : "+str(len(liste_suppression))+"]\n")
        for item in liste_suppression:
            logs.write("%s\n" % item)    
        liste_suppression
        logs.write("\n")

def threading_telechargements(nb_threads, images, session):
    threads = [None]*nb_threads
    results = [None]*nb_threads
    for i in range(len(threads)):
        threads[i] = threading.Thread(target=telecharger_images, args=(images[i], session, results, i))
        threads[i].start()
    
    liste_fail = []
    for i in range(len(threads)):
        threads[i].join()
        liste_fail += results[i]
    return liste_fail

if __name__ == '__main__':
    print("Chargement des modules de décollage...")
    # Configuration
    config, date_debut_batch, date_fin_batch, save_folder, nb_threads = chargement_config()
    maj = False
    # Récupération des paramètres de la cmd
    recuperer_arguments(sys.argv[1:])
    print("  Plan de vol du "+str(date_debut_batch)+" au "+str(date_fin_batch)+" validé.")
    print("  Backup de la cartographie interstellaire dans le sas "+str(save_folder)+"...")
    dic_sign_md5 = dr.generate_or_load_md5(save_folder)
    print("     Découpage en parsec terminé")

    # Variables
    print("Connexion à la base de données universelle...")
    session = init_session()
    print("Authentification du vaisseau...")
    archive_photos = session.get('https://apod.nasa.gov/apod/archivepix.html').text
    archive_photos = BeautifulSoup(archive_photos, 'html.parser')
    
    # Création du répertoire de sauvegarde si besoin
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    print("   Land rover embarqué.")
    
    print("Validation du plan de vol...")

    liste_articles = get_liens_articles(archive_photos)
    print("  ",len(liste_articles),"documents détectés.")
    
    print("Vérification des modules d'amarrage...")
    liste_images, liste_refus = threading_liens_images(nb_threads, liste_articles, session)
    print("  ",len(liste_images)," ancres connectées au système central.")
    
    print("Contournement du pare-feu et surcharge du réacteur principal...")
    images = tu.decouper_liste_threads(liste_images, nb_threads)
    liste_fail = threading_telechargements(nb_threads, images, session)
    
    print("   Annihilation des résidus de transfert...")
    liste_suppression, dic_sign_md5 = dr.find_duplicates_folder(dic_sign_md5, save_folder)
    for el in liste_suppression:
        print("      Fret "+el+" largué.")
    
    print("   Ouverture d'un trou de ver...")
    dr.save_dico_md5(dic_sign_md5)
    
    print(str(len(liste_refus))," intrus détectés. Veuillez monter sur le pont de toute urgence.")
    sauvegarder_log(date_debut_batch, date_fin_batch, liste_articles, liste_images, liste_refus, liste_fail, liste_suppression)
    print("   Menaces erradiquées, reprise du protocole d'initialisation.")
    
    print("Systèmes principaux      : 100%")
    print("Systèmes auxiliaires     : 100%")
    print("Modules de survie        : 100%")
    print("Préparation du décollage : 100%")
    
    if maj:
        print("   Partage de la connaissance validé.")
        sauver_config(config, date_fin_batch)
        print("   Données sauvegardées.")
    else:
        print("Voulez-vous mettre à jour la configuration de l'ordinateur de bord pour notre prochain voyage ? y/n")
        sauvegarder_config = input("")
        if sauvegarder_config == 'y':
            print("   Partage de la connaissance validé.")
            sauver_config(config, date_fin_batch)
            print("   Données sauvegardées.")
        else:
            print("   Abandon du partage de connaissance.")
    
    print("Bon vol, Capitaine.")