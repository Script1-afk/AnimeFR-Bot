<div align="center">

```
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     🎌  A N I M E F R   B O T  🎌                       ║
    ║                                                          ║
    ║     Le bot Telegram ultime pour les passionnés d'anime   ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
```

# 🎌 AnimeFR Bot

**Le bot Telegram le plus complet pour gérer un canal anime francophone.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/animeFR2026)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-6.0-ff6b6b?style=for-the-badge)](#-changelog)

---

**[📡 Canal Telegram](https://t.me/animeFR2026)** · **[📖 Documentation](#-installation)** · **[🐛 Signaler un bug](https://github.com/Script1-afk/AnimeFR-Bot/issues)** · **[💡 Suggestions](https://github.com/Script1-afk/AnimeFR-Bot/issues)**

</div>

---

## ✨ Pourquoi AnimeFR Bot ?

AnimeFR Bot transforme votre canal Telegram en une **plateforme anime complète**. Plus besoin de rédiger manuellement chaque post : une seule commande suffit pour rechercher, générer et publier un anime avec description IA, image, liens de visionnage et boutons interactifs.

<div align="center">

| 🤖 IA Intégrée | 📱 Mobile-First | 🛡️ Admin Pro | 🎬 Sources Streaming |
|:---:|:---:|:---:|:---:|
| GPT-4o génère synopsis, avis et tags automatiquement | Interface optimisée pour Termux & mobile | 4 niveaux de rôles, logs, backup auto | Franime, Anime-Sama, VoirAnime |

</div>

---

## 🚀 Fonctionnalités

### 📝 Publication Intelligente

```
/auto Jujutsu Kaisen
```

Le bot fait **tout automatiquement** :
1. 🔍 Recherche sur MyAnimeList
2. 🤖 Génère synopsis FR, avis, tags via OpenAI
3. 🎬 Ajoute les liens de visionnage
4. 📸 Publie avec image + boutons interactifs
5. ✅ Terminé en 5 secondes !

### 🎯 Toutes les fonctionnalités

<details>
<summary><b>📝 Publication & Contenu</b></summary>

- Publication manuelle avec 16 champs détaillés
- Publication automatique via IA (`/auto`)
- 7 templates visuels (Standard, Compact, Premium, Minimal, Mobile, Elegant, Neon)
- Posts programmés avec date/heure
- Galerie d'images, trailers
- Tags personnalisés
- Accroche IA en haut de chaque post

</details>

<details>
<summary><b>🤖 Intelligence Artificielle</b></summary>

- Génération de synopsis en français
- Avis personnalisé par IA
- Tags et catégories automatiques
- Suggestions d'anime similaires (`/aisuggest`)
- Récap hebdomadaire (`/airecap`)
- Auto-publication de la saison (`/autopublish`)

</details>

<details>
<summary><b>🎬 Sources de Visionnage</b></summary>

- Liens Franime, Anime-Sama, VoirAnime
- Boutons "Regarder" sous chaque post
- Détection automatique des sources
- Commande `/sources` dédiée

</details>

<details>
<summary><b>👥 Communauté</b></summary>

- Likes / Dislikes avec compteur temps réel
- Favoris personnels
- Notation communautaire (1-10)
- Sondages interactifs
- Quiz anime
- Classements (top likes, vues, notes)
- Suivi d'anime + notifications nouveaux épisodes

</details>

<details>
<summary><b>🔍 Recherche & Données</b></summary>

- Recherche MAL intégrée
- Recherche locale avec filtres
- Recherche avancée (genre + statut + note)
- Comparaison de 2 anime
- Calendrier des sorties
- Fiches détaillées

</details>

<details>
<summary><b>🛡️ Administration</b></summary>

- Panel admin interactif (`/panel`)
- 4 rôles : Superadmin, Admin, Modérateur, Éditeur
- Permissions granulaires (poster, modifier, supprimer, programmer)
- Logs complets de toutes les actions
- Backup automatique + restauration
- Mode maintenance
- Blacklist / Whitelist
- Export / Import JSON
- Broadcast (annonces)
- Dashboard avec statistiques et graphes
- Purge des anciennes données

</details>

---

## 📦 Versions

| Version | Nom | Highlights |
|:---:|---|---|
| **v6.0** 🆕 | Publication Auto & IA | OpenAI, `/auto`, liens streaming, auto-publish |
| v5.0 | Mobile & Admin Pro | Panel interactif, mode mobile, export/import |
| v4.0 | Communauté | Favoris, notation, sondages, quiz, comparaison |
| v3.0 | Admin & Technique | Dashboard, backup auto, maintenance, templates |

> 📁 Toutes les versions sont disponibles dans le dossier [`versions/`](versions/)

---

## ⚡ Installation rapide

### Prérequis

- Python 3.10+
- Token Telegram (via [@BotFather](https://t.me/BotFather))
- Clé API OpenAI (optionnel, pour les fonctionnalités IA)

### 1. Cloner le repo

```bash
git clone https://github.com/Script1-afk/AnimeFR-Bot.git
cd AnimeFR-Bot
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

```bash
cp .env.example .env
nano .env
```

```env
BOT_TOKEN=votre_token_telegram
OPENAI_API_KEY=votre_cle_openai
```

### 4. S'ajouter comme superadmin

```bash
python3 -c "
import database as db
db.init_db()
db.add_admin(VOTRE_ID, 'votre_username', 'superadmin', 0)
"
```

### 5. Lancer

```bash
python3 bot.py
```

---

## 📱 Déploiement

<details>
<summary><b>📱 Termux (Android)</b></summary>

```bash
pkg update && pkg install python git
git clone https://github.com/Script1-afk/AnimeFR-Bot.git
cd AnimeFR-Bot
pip install -r requirements.txt
cp .env.example .env && nano .env
screen -S animefr
python3 bot.py
# Détacher : Ctrl+A puis D
```

</details>

<details>
<summary><b>🖥️ VPS avec systemd</b></summary>

```bash
sudo nano /etc/systemd/system/animefr-bot.service
```

```ini
[Unit]
Description=AnimeFR Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AnimeFR-Bot
EnvironmentFile=/home/ubuntu/AnimeFR-Bot/.env
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now animefr-bot
```

</details>

<details>
<summary><b>🔄 PM2 (Node.js)</b></summary>

```bash
pm2 start bot.py --interpreter python3 --name animefr
pm2 save && pm2 startup
```

</details>

---

## 🏗️ Architecture

```
AnimeFR-Bot/
├── bot.py              # 🎯 Fichier principal (2200+ lignes)
├── config.py           # ⚙️ Configuration (tokens via env)
├── database.py         # 💾 SQLite avec WAL, backup, export
├── formatter.py        # 🎨 7 templates de posts
├── jikan.py            # 🌐 API MyAnimeList (Jikan)
├── openai_helper.py    # 🤖 Module IA (génération de contenu)
├── sources.py          # 🎬 Liens de visionnage
├── requirements.txt    # 📦 Dépendances Python
├── start.sh            # 🚀 Script de démarrage
├── .env.example        # 🔑 Template variables d'environnement
├── .gitignore          # 🚫 Fichiers exclus
├── LICENSE             # 📄 MIT License
├── CONTRIBUTING.md     # 🤝 Guide de contribution
└── versions/           # 📚 Versions précédentes
    ├── v3/
    ├── v4/
    └── v5/
```

---

## 🎨 Exemple de post généré

```
💬 Un chef-d'œuvre du shōnen moderne qui redéfinit le genre !

╔══════════════════════════════╗
║  🎌 JUJUTSU KAISEN          ║
║  呪術廻戦                     ║
╚══════════════════════════════╝

📖 Synopsis :
Dans un monde où les malédictions naissent des émotions
négatives des humains, Yuji Itadori, un lycéen doté d'une
force physique hors du commun, se retrouve plongé dans
l'univers des exorcistes après avoir avalé un doigt de
Sukuna, le roi des fléaux...

🎭 Personnages : Yuji Itadori, Megumi Fushiguro, Nobara
    Kugisaki, Gojo Satoru, Sukuna

🏢 Studio : MAPPA
📅 Date : Octobre 2020
📺 Épisodes : 24
📊 Statut : ✅ Terminé
🏷️ Genres : Action, Fantasy, Surnaturel
⭐ Note : ★★★★☆ 8.7/10

💭 Avis : Un anime qui allie combats spectaculaires,
personnages attachants et un système de pouvoir original.

🏷️ Tags : #shonen #combat #malédictions #MAPPA

▶️ Regarder :
▶️ Franime
▶️ Anime-Sama
▶️ VoirAnime

[👍 12] [👎 1] [⭐ Favoris] [📊 Noter]
```

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez le [guide de contribution](CONTRIBUTING.md).

---

## 📄 License

Ce projet est sous licence [MIT](LICENSE) — créé avec ❤️ par **Prince Ibrahim Wellot-Samba**.

---

<div align="center">

**⭐ Si ce projet vous plaît, n'hésitez pas à mettre une étoile !**

[![Telegram](https://img.shields.io/badge/Rejoindre-@animeFR2026-26A5E4?style=for-the-badge&logo=telegram)](https://t.me/animeFR2026)

</div>
