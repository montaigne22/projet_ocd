# The files of Odoo on an S3 storage (attachment_s3: Cloudflare R2, AWS S3, Backblaze B2, MinIO)
STORAGE = {
    "%(synced)s files on the bucket (%(size)s GB) · %(pending)s to send · %(error)s not sent yet":
        "%(synced)s fichiers sur le bucket (%(size)s Go) · %(pending)s à envoyer · %(error)s pas encore envoyés",
    "%s files noted to send: they leave a little at a time, the progress shows here.":
        "%s fichiers notés à envoyer : ils partent petit à petit, la progression s'affiche ici.",
    "AWS S3": "AWS S3",
    "Access Key ID": "ID de la clé d'accès",
    "Account ID": "ID du compte",
    "All the files (the safest)": "Tous les fichiers (le plus sûr)",
    "All the files: the disk keeps a copy (the safest). The files read lately: the server keeps only this size, the others come back from the bucket when they are read.":
        "Tous les fichiers : le disque garde une copie (le plus sûr). Les fichiers lus récemment : le serveur ne garde que cette taille, les autres reviennent du bucket quand on les lit.",
    "Attachment": "Pièce jointe",
    "Backblaze B2": "Backblaze B2",
    "Config Settings": "Paramètres de configuration",
    "Error": "Erreur",
    "State": "État",
    "https://": "https://",
    "Bring the files back on this server": "Rapatrier les fichiers sur ce serveur",
    "Bucket": "Bucket",
    "Cloudflare R2": "Cloudflare R2",
    "Cloudflare R2: R2 › Manage API tokens › Create a token « Object Read and Write » for the bucket; the Account ID is on the page R2 › Overview.":
        "Cloudflare R2 : R2 › Gérer les jetons d'API › Créer un jeton « Lecture et écriture d'objets » pour le bucket ; l'ID du compte est sur la page R2 › Vue d'ensemble.",
    "Cloudflare R2: the Account ID (Cloudflare › R2 › Overview).": "Cloudflare R2 : l'ID du compte (Cloudflare › R2 › Vue d'ensemble).",
    "Empty for Cloudflare R2 (made from the Account ID) and AWS S3.": "Vide pour Cloudflare R2 (fait à partir de l'ID du compte) et AWS S3.",
    "Endpoint": "Adresse du service",
    "Every file missing on this server is taken back from the bucket (the disk must have the room). Go on?":
        "Chaque fichier qui manque sur ce serveur est repris du bucket (le disque doit avoir la place). Continuer ?",
    "File": "Fichier",
    "File On The S3 Storage": "Fichier sur le stockage S3",
    "Files On An S3 Storage": "Fichiers sur un stockage S3",
    "Files On An S3 Storage (Cloudflare R2, AWS S3, Backblaze B2, MinIO)": "Fichiers sur un stockage S3 (Cloudflare R2, AWS S3, Backblaze B2, MinIO)",
    "Files on an S3 storage": "Fichiers sur un stockage S3",
    "Files on an S3 storage: send, check, clean": "Fichiers sur un stockage S3 : envoyer, vérifier, nettoyer",
    "Folder": "Dossier",
    "From The Configuration File": "Depuis le fichier de configuration",
    "GB": "Go",
    "Give the bucket and its two keys first.": "Donne d'abord le bucket et ses deux clés.",
    "Given by the configuration file of the server (they win): %s.": "Donnés par le fichier de configuration du serveur (ils l'emportent) : %s.",
    "Keep On The Server": "Garder sur le serveur",
    "Keep on the server": "Garder sur le serveur",
    "Last Error": "Dernière erreur",
    "MinIO": "MinIO",
    "Next Try": "Prochain essai",
    "Not Sent": "Pas envoyé",
    "Noted At": "Noté le",
    "On The Bucket": "Sur le bucket",
    "One row per file.": "Une ligne par fichier.",
    "Other S3 storage": "Autre stockage S3",
    "Progress": "Progression",
    "Region": "Région",
    "Secret Access Key": "Clé d'accès secrète",
    "Send the files now": "Envoyer les fichiers maintenant",
    "Size": "Taille",
    "Size On The Server (GB)": "Taille sur le serveur (Go)",
    "Storage": "Stockage",
    "Synced At": "Envoyé le",
    "Test the connection": "Tester la connexion",
    "The bucket": "Le bucket",
    "The bucket answers: a file was written, read and deleted.": "Le bucket répond : un fichier a été écrit, lu et supprimé.",
    "The bucket does not answer: %s": "Le bucket ne répond pas : %s",
    "The copy on the bucket does not have the size of the file.": "La copie sur le bucket n'a pas la taille du fichier.",
    "The copy on the bucket is not the same file (MD5).": "La copie sur le bucket n'est pas le même fichier (MD5).",
    "The file is not on the disk of this server.": "Le fichier n'est pas sur le disque de ce serveur.",
    "The file read back is not the one written.": "Le fichier relu n'est pas celui écrit.",
    "The files are copied on the bucket and read from it when the server misses them: give the keys, test, then turn on and save. The files already there leave a little at a time.":
        "Les fichiers sont copiés sur le bucket et relus depuis lui quand le serveur ne les a plus : donne les clés, teste, puis active et enregistre. Les fichiers déjà là partent petit à petit.",
    "The files missing on this server are taken back from the bucket by the scheduled task.":
        "Les fichiers qui manquent sur ce serveur sont repris du bucket par la tâche planifiée.",
    "The files of Odoo copied on an S3 bucket and read from it: give the keys, the files already there are sent by themselves":
        "Les fichiers d'Odoo copiés sur un bucket S3 et relus depuis lui : donne les clés, les fichiers déjà là partent tout seuls",
    "The files read lately": "Les fichiers lus récemment",
    "The files stay on the disk of the server too, or only the files read lately up to a size: the others are taken back from the bucket when they are read.":
        "Les fichiers restent aussi sur le disque du serveur, ou seulement les fichiers lus récemment jusqu'à une taille : les autres sont repris du bucket quand on les lit.",
    "The folder of this database in the bucket. Empty: the name of the database.": "Le dossier de cette base dans le bucket. Vide : le nom de la base.",
    "The server needs boto3: pip install boto3.": "Le serveur a besoin de boto3 : pip install boto3.",
    "To Send": "À envoyer",
    "Tries": "Essais",
    "Turn on « Files on an S3 storage » and save first.": "Active d'abord « Fichiers sur un stockage S3 » et enregistre.",
    "« auto » for Cloudflare R2; e.g. eu-west-3 for AWS S3.": "« auto » pour Cloudflare R2 ; ex. eu-west-3 pour AWS S3.",
}

STORAGE_DESCRIPTION = """
Fichiers sur un stockage S3
===========================

Les fichiers d'Odoo (photos, vidéos, PDF, pièces jointes) sont gardés sur un
bucket S3 : Cloudflare R2, AWS S3, Backblaze B2, Wasabi, MinIO ou tout
stockage S3.

- Paramètres › Paramètres généraux › Fichiers sur un stockage S3 : le
  fournisseur, le bucket et ses clés (ou dans le fichier de configuration du
  serveur), « Tester la connexion », puis activer.
- Chaque nouveau fichier est copié sur le bucket juste après son
  enregistrement, vérifié (taille et MD5), et renvoyé plus tard quand le
  réseau coupe. Les fichiers déjà là partent en arrière-plan, petit à petit,
  avec leur progression dans les paramètres.
- Odoo continue de travailler comme avant sur le disque du serveur : un
  fichier qui manque sur le disque (un autre serveur, un nouveau serveur, un
  disque perdu) est repris du bucket quand on le lit. La copie sur le
  serveur peut rester (le plus sûr), ou le serveur ne garde que les fichiers
  lus récemment (une taille en Go).
- Un fichier supprimé dans Odoo est supprimé du bucket un jour plus tard ;
  « Rapatrier les fichiers sur ce serveur » avant de quitter le bucket.
- Un bucket pour plusieurs bases et plusieurs serveurs : un dossier par base.
"""
