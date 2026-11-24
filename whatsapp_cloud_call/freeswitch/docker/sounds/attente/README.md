# La musique d'attente

La musique que le client entend pendant qu'il attend un conseiller. La voix d'attente du dossier
`../voix/` passe par-dessus. Facultatif : sans fichier ici, le client entend la musique de FreeSWITCH.

```
attente/
├── README.md        ce fichier
├── 1-musique.mp3    la première musique
└── 2-musique.mp3    la suivante, puis de nouveau la première…
```

## Quand le client l'entend

- Dès qu'il attend un conseiller, et pendant que son téléphone sonne chez les conseillers.
- Les fichiers passent **l'un après l'autre, dans l'ordre de leur nom**, en boucle : les numéroter
  (`1-…`, `2-…`).
- L'attente marche comme une radio : tous les clients qui attendent entendent le même flux. Un client
  qui arrive entend la musique là où elle en est.
- Si un numéro a sa propre musique d'attente dans Odoo, elle remplace celle de ce dossier pour ce
  numéro.

## Le choix de la musique

- **Une musique libre de droits** dont la licence permet l'usage commercial, ou une musique à OCD. Pas
  un titre de la radio : il est protégé.
- **Sans paroles** : les phrases à dire vont dans `../voix/`, pour qu'elles passent par-dessus la
  musique toutes les 30 secondes.
- **Un fichier assez long** (2 à 5 minutes), ou plusieurs, pour qu'un client qui attend n'entende pas
  la même boucle.
- **Un volume modéré**, celui des voix : le serveur n'égalise pas le volume des fichiers de ce dossier.

## Les règles

- **MP3 ou WAV** : le serveur convertit les MP3 au démarrage (mono, 16 kHz, la qualité du
  téléphone) ; un WAV est pris tel quel (le mieux : mono, 16 kHz).
- **Noms libres** : lettres sans accent, chiffres, `-`, `_`, `.`, sans espace ni accent (par ex.
  `1-musique.mp3`). Sinon le fichier est écarté, et le journal affiche « Sounds: attente/... skipped ».
- Après un changement, depuis `docker/`, quand personne n'est en appel :
  `docker compose up -d --force-recreate freeswitch`. Le journal affiche alors « Music while waiting: the
  files of sounds/attente ».

Voir aussi `../README.md` (la structure du dossier) et le guide du serveur, partie 5.
