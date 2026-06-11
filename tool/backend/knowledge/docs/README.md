# Documents sources (RAG)

Dépose ici les **fichiers sources** de connaissances : `.pdf`, `.txt`, `.md`.
Ils sont automatiquement découpés en chunks, indexés en **BM25** et interrogés
par l'assistant via l'outil `search_knowledge`.

## Importer les sources du NotebookLM

Le notebook NotebookLM n'est **pas accessible directement** par l'outil (privé,
derrière l'authentification Google, pas d'API publique). Il faut donc exporter
ses sources ici :

1. Ouvre le notebook dans NotebookLM.
2. Pour chaque source (panneau de gauche) :
   - **PDF déjà importé** → récupère le PDF d'origine et dépose-le ici.
   - **Site web / Google Doc / texte collé** → ouvre la source, sélectionne le
     texte, colle-le dans un fichier `.txt` ou `.md` ici (un fichier par source,
     nom parlant : `manuel-m620.txt`, `suspension-kinematics.md`…).
   - Astuce : tu peux aussi imprimer une page web en PDF et la déposer ici.
3. Réindexe : `POST /api/knowledge/reindex` (ou redémarre le backend).
4. Vérifie : `GET /api/knowledge/stats` (nombre de fichiers + chunks par source).

## Bonnes pratiques

- **Un fichier = une source** cohérente (le nom du fichier devient un tag et la
  citation `source` dans les résultats).
- Préfère le **texte sélectionnable** : un PDF scanné en image ne donne aucun
  texte (pas d'OCR). Dans ce cas, copie-colle le contenu en `.txt`.
- Les fichiers ici ne sont **pas** suivis par git (voir `.gitignore`) : ce sont
  tes sources de travail, pas du code.
