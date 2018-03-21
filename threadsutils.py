def decouper_liste_threads(liste_images, nb_threads):
    q = len(liste_images)//nb_threads
    r = len(liste_images)%nb_threads
    images = []
    for i in range(nb_threads):
        a = i*q
        b = a + q
        images.append(liste_images[a:b])
    cpt = 0
    for i in range(r):
        cur = nb_threads*q+i
        images[cpt].append(liste_images[cur])
        cpt += 1
        if cpt == nb_threads:
            cpt = 0
    return images