# Les messages enregistrés du serveur d'appels

Ce dossier contient ce qu'entendent les clients qui appellent un numéro WhatsApp : l'accueil,
l'annonce d'enregistrement, la messagerie… et, dans ses deux sous-dossiers, la voix et la musique
d'attente. Tous les fichiers sont **facultatifs**.

**D'abord Odoo.** Le plus simple est de donner les messages dans Odoo : compte WhatsApp › onglet
Appels › « Messages des appels ». On les donne numéro par numéro, et le serveur les prend dans la
minute, sans redémarrer. Ce dossier sert de **repli** : un message qu'Odoo ne donne pas pour un numéro
est pris ici. S'il n'est pas ici non plus, le client entend une tonalité courte (rien pour la voix
d'attente, et la musique de FreeSWITCH pour l'attente).

Sur le serveur, c'est le dossier `docker/sounds/` du serveur d'appels : la valeur `OCD_SOUNDS_DIR=./sounds`
du `.env`, à garder.

## La structure

```
sounds/
├── README.md             ce fichier
├── accueil.mp3           dès que l'appel arrive
├── enregistrement.mp3    l'annonce : l'appel est enregistré
├── reconnexion.mp3       le conseiller a été coupé, l'appel revient
├── messagerie.mp3        personne de disponible : laisser un message après le bip
├── indisponible.mp3      personne de disponible, et pas de messagerie
├── voix/                 la voix d'attente, par-dessus la musique (voir voix/README.md)
│   ├── README.md
│   ├── 1-patientez.mp3
│   └── 2-occupes.mp3
└── attente/              la musique d'attente (voir attente/README.md)
    ├── README.md
    └── 1-musique.mp3
```

## Les fichiers de ce dossier

| Fichier | Quand le client l'entend | Durée conseillée | Texte proposé | En anglais |
|---|---|---|---|---|
| `accueil.mp3` | dès que l'appel arrive | environ 6 s ; 12 s au plus avec les deux langues | « Bonjour et bienvenue chez OCD Live. Un conseiller va vous répondre dans un instant. » | “Hello and welcome to OCD Live. An advisor will be with you in a moment.” |
| `enregistrement.mp3` | après l'accueil, et quand il décroche un appel de l'entreprise, si les appels sont enregistrés (Odoo) | environ 4 s ; 8 s au plus avec les deux langues | « Pour la qualité de notre service, cet appel est enregistré. » | “To help us improve our service, this call is recorded.” |
| `reconnexion.mp3` | le conseiller a été coupé, pendant que l'appel revient | environ 3 s ; 8 s au plus avec les deux langues | « Un instant, nous vous reconnectons à votre conseiller. » | “One moment please, we are reconnecting you to your advisor.” |
| `messagerie.mp3` | personne de disponible, avant le bip | environ 8 s ; 15 s au plus avec les deux langues | « Nos conseillers sont tous occupés. Laissez votre message après le bip : nous vous rappelons dès que possible. » | “All our advisors are busy. Please leave your message after the beep, and we will call you back as soon as possible.” |
| `indisponible.mp3` | personne de disponible, et pas de messagerie | environ 8 s ; 15 s au plus avec les deux langues | « Nos conseillers sont tous occupés. Écrivez-nous sur WhatsApp, à ce même numéro : nous vous répondons rapidement. » | “All our advisors are busy. Send us a message on WhatsApp, at this same number, and we will reply quickly.” |

**En deux langues** : chaque message est un seul fichier. Pour des clients francophones et
anglophones, enregistrer les deux phrases dans le même fichier : le français d'abord, une courte
pause, puis l'anglais.

**Les durées conseillées** : le client attend pendant que le message passe, avant d'être mis en
relation. Un message court est mieux reçu : dire le texte posément, sans le rallonger. Au-delà de la
durée « au plus », raccourcir le texte ou garder une seule langue. Pour un message donné dans Odoo,
Odoo mesure la durée du fichier et le signale en orange quand il est trop long.

| Message | En une langue | Au plus, avec les deux langues |
|---|---|---|
| Accueil | environ 6 s | 12 s |
| Annonce d'enregistrement | environ 4 s | 8 s |
| Voix d'attente (`voix/`), chacune | environ 7 s | 15 s |
| Conseiller coupé | environ 3 s | 8 s |
| Messagerie | environ 8 s | 15 s |
| Personne de disponible | environ 8 s | 15 s |
| Musique d'attente (`attente/`) | 2 à 5 minutes par fichier, ou plusieurs fichiers | pas de limite |

## Les règles

- **MP3 ou WAV** : au démarrage, le serveur convertit les MP3 en WAV (mono, 16 kHz) ; un WAV est
  pris tel quel (le mieux : mono, 16 kHz). Si un WAV et un MP3 portent le même nom, le WAV l'emporte. Le volume n'est pas
  égalisé (il l'est pour les messages donnés dans Odoo), donc préparer des fichiers au même volume.
- **À la racine, ces noms exacts, en minuscules**, suivis de `.mp3` ou `.wav`. `Accueil.mp3`,
  `accueil OCD.mp3` ou `accueil.mp3.mp3` ne sont pas trouvés, et le client entend une tonalité à la
  place.
- **Partout** : lettres sans accent, chiffres, `-`, `_`, `.`, sans espace ni accent. Sinon le fichier
  est écarté, et le journal affiche « Sounds: ... skipped ».
- **Sous Windows** : afficher les extensions (Explorateur › Affichage › « Extensions de noms de
  fichiers »), sinon un fichier peut s'appeler en vrai `accueil.mp3.mp3`.
- Les autres fichiers, comme ces README.md, sont ignorés par le serveur.

## Appliquer un changement

Après avoir posé ou changé des fichiers, quand personne n'est en appel, depuis le dossier `docker/` :

```bash
docker compose up -d --force-recreate freeswitch
```

```bash
docker compose logs freeswitch | grep -E "Sounds|Music while|Voice while"
```

Le journal affiche « Sounds ready: N file(s) », puis « Music while waiting » et « Voice while waiting »
quand `attente/` et `voix/` ont des fichiers. Il dit aussi pourquoi un fichier a été écarté.

Pour les fichiers copiés depuis Windows : la commande de correction des fins de ligne (guide du
serveur, partie 3A) laisse les `.mp3` et les `.wav` de côté, sinon elle les abîmerait.

Les fichiers audio ne sont pas dans le dépôt git : chaque serveur a les siens. Seuls ces README.md y
sont. Plus de détails dans le guide du serveur, partie 5.
