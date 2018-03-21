import os
import hashlib
import pickle

FICHIER_MD5_SIGNATURES = 'signatures.sav'

def md5_file(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def remove_duplicates(dossier):
    unique = []
    liste_doublons = []
    liste_fichiers = os.listdir(dossier)
    for filename in liste_fichiers:
        filehash = md5_file(os.path.join(dossier+'/'+filename))
        if filehash not in unique: 
            unique.append(filehash)
        else: 
            liste_doublons.append(filename)
            os.remove(os.path.join(dossier+'/'+filename))
    return liste_doublons

def find_duplicates_folder(dico, dossier):
    liste_fichiers = os.listdir(dossier)
    liste_suppression = []
    for filename in liste_fichiers:
        filehash = md5_file(os.path.join(dossier+'/'+filename))
        if filehash in dico:
            if filename != dico[filehash]:
                try:
                    liste_suppression.append(filename)
                    os.remove(os.path.join(dossier+'/'+filename))
                except Exception:
                    print("      Erreur lors de la suppression "+filename)
        else:
            dico[filehash] = filename
    return liste_suppression, dico

def save_dico_md5(dico):
    with open(FICHIER_MD5_SIGNATURES, 'wb') as f:
        pickle.dump(dico, f)
    
def load_dico_md5():
    with open(FICHIER_MD5_SIGNATURES, 'rb') as f:
        dico = pickle.load(f)
    return dico

def reset_dico_md5():
    os.remove(FICHIER_MD5_SIGNATURES)

def generate_md5_folder(dossier):
    dict_md5 = {}
    liste_fichiers = os.listdir(dossier)
    for filename in liste_fichiers:
        m = md5_file(os.path.join(dossier+'/'+filename))
        dict_md5[m] = filename
    save_dico_md5(dict_md5)
    return dict_md5

def generate_or_load_md5(dossier):
    liste_fichiers = os.listdir()
    if FICHIER_MD5_SIGNATURES in liste_fichiers:
        return load_dico_md5()
    else:
        return generate_md5_folder(dossier)
    
if __name__ == '__main__':
    liste_doublons = remove_duplicates('./images')
    for el in liste_doublons:
        print(el)

##TODO
# générer les md5 de tout le dossier --> avec threads
# générer les md5 de la liste des fichiers téléchargés --> avec threads
# regarder quels sont les doublons --> avec threads ? a priori ça ne devrait pas être trop long ?
# sauvegarder la liste des doublons (les noms des fichiers)
# déplacer ou supprimer les doublons, en gardant le fichier le plus ancien
# Attention si dossier dans le répertoire ça plante !
# stocker le dossier en plus du fichier ?