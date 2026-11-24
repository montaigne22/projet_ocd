# La voix d'attente

Pendant que le client attend un conseiller, il entend la musique (dossier `../attente/`) et,
**par-dessus**, les messages de ce dossier, l'un après l'autre. Facultatif : sans fichier ici, le client
n'entend que la musique.

```
voix/
├── README.md         ce fichier
├── 1-patientez.mp3   la première voix
└── 2-occupes.mp3     la suivante, puis de nouveau la première…
```

## Quand le client l'entend

- **Toutes les 30 secondes** par défaut. Le réglage est dans Odoo : compte WhatsApp › onglet Appels ›
  « Voix d'attente toutes les (secondes) », de 10 à 600. `OCD_HOLD_VOICE_EVERY` du `.env` ne sert qu'au
  démarrage, tant que le serveur n'a pas reçu les réglages d'Odoo.
- Les fichiers passent **l'un après l'autre, dans l'ordre de leur nom**, en boucle : les numéroter
  (`1-…`, `2-…`).
- L'attente marche comme une radio : tous les clients qui attendent entendent le même flux. Un client
  entend donc une voix au plus 30 secondes après son arrivée, parfois tout de suite.
- Si un numéro a ses propres voix d'attente dans Odoo, elles remplacent celles de ce dossier pour ce
  numéro.

## Textes proposés

| Fichier | Texte proposé | En anglais |
|---|---|---|
| `1-patientez.mp3` | « Merci de patienter, un conseiller va vous répondre dans un instant. » | “Thank you for holding, an advisor will be with you in a moment.” |
| `2-occupes.mp3` | « Tous nos conseillers sont occupés. Merci de rester en ligne, votre appel est important pour nous. » | “All our advisors are busy. Please stay on the line, your call is important to us.” |

**Durée conseillée** : environ 7 secondes par fichier en une langue, **15 secondes au plus** avec les
deux langues (le français d'abord, une courte pause, puis l'anglais). La voix revient toutes les 30
secondes : plus longue, elle couvrirait la musique presque tout le temps. Au-delà, raccourcir le texte
ou garder une seule langue. Dans Odoo, la durée de chaque voix est mesurée et signalée en orange quand
elle dépasse 15 secondes.

## Les règles

- **MP3 ou WAV** : le serveur convertit les MP3 au démarrage ; un WAV est pris tel quel (le mieux :
  mono, 16 kHz).
- **Noms libres** : lettres sans accent, chiffres, `-`, `_`, `.`, sans espace ni accent (par ex.
  `1-patientez.mp3`). Sinon le fichier est écarté, et le journal affiche « Sounds: voix/... skipped ».
- **Le même volume que la musique** : le serveur n'égalise pas le volume des fichiers de ce dossier.
- Après un changement, depuis `docker/`, quand personne n'est en appel :
  `docker compose up -d --force-recreate freeswitch`. Le journal affiche alors « Voice while waiting: the
  files of sounds/voix, every 30 s ».

Voir aussi `../README.md` (la structure du dossier) et le guide du serveur, partie 5.
