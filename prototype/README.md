# Prototype OCD Live

## `design-valide/`

Le design validé avec l'équipe OCD : un fichier par écran (`*.dc.html`), plus `canvas.json` qui
range les écrans sur la toile. Les noms des fichiers sont repris dans [`docs/ECRANS.md`](../docs/ECRANS.md)
pour dire où chaque écran est fait dans le code.

- `Bo*` : back-office de l'équipe (sur ordinateur).
- `Equipe*` : écrans de l'équipe sur téléphone.
- Les autres : pages du site (vendeurs, clients, livreurs).

Ces fichiers s'ouvrent dans l'outil de design (canvas) où ils ont été faits : ils chargent un
`support.js` qui n'est pas ici. On peut quand même les lire dans un éditeur : chaque fichier contient
le HTML de l'écran avec ses styles, puis, en bas, la logique et les données d'exemple.
Le logo référencé `/_blob/273c64c79958def7341794eb4577315c` est dans `design-valide/_blob/`.

## `prototype-interactif/`

`index.html` : le prototype interactif (téléphone de la vendeuse à gauche, écran de l'équipe à
droite). Il s'ouvre directement dans un navigateur.
