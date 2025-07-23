# Newsletter Manager

Un gestionnaire intelligent de newsletters utilisant le protocole A2A (Agent-to-Agent) pour automatiser le traitement et la synthèse des emails de type newsletter.

## 🎯 Objectif

Développer une application multi-agents personnelle qui :
- Se connecte automatiquement à plusieurs boîtes email (3 Gmail + 1 Hotmail)
- Identifie et traite les newsletters non lues
- Génère des résumés intelligents quotidiens
- Marque automatiquement les emails traités comme lus

## 🚀 Fonctionnalités

### Core Features
- **Connexion multi-comptes** : Intégration avec 3 comptes Gmail + 1 compte Hotmail
- **Détection intelligente** : Identification automatique des emails de type newsletter
- **Résumé automatique** : Génération quotidienne à 8h00 d'un email de synthèse
- **Interface de contrôle** : Déclenchement manuel du processus de résumé
- **Marquage automatique** : Les emails résumés sont automatiquement marqués comme lus

### Architecture Multi-Agents (A2A)
- **Agent Email Collector** : Collecte des emails depuis les différentes boîtes
- **Agent Newsletter Detector** : Classification et détection des newsletters
- **Agent Content Summarizer** : Génération des résumés intelligents
- **Agent Scheduler** : Gestion des tâches programmées
- **Agent Interface** : Interface utilisateur et API de contrôle

## 🛠️ Stack Technique

### Environnement
- **Plateforme** : macOS (MacBook Air M2 - Apple Silicon)
- **Langage** : Python 3.11+
- **Architecture** : Multi-agents avec protocole A2A

### Technologies Prévues
- **Email APIs** : 
  - Gmail API (Google Workspace)
  - Microsoft Graph API (Hotmail/Outlook)
- **Framework A2A** : À déterminer (possiblement custom ou framework existant)
- **IA/ML** : 
  - OpenAI GPT pour la génération de résumés
  - Classification de texte pour la détection de newsletters
- **Scheduling** : APScheduler ou Celery
- **Interface** : FastAPI + interface web simple ou CLI
- **Storage** : SQLite pour les métadonnées, logs et configuration

## 📋 Workflow

### Processus Automatique (8h00 quotidien)
1. **Collecte** : Connexion aux 4 boîtes email
2. **Filtrage** : Identification des emails non lus de type newsletter
3. **Analyse** : Extraction et résumé du contenu
4. **Synthèse** : Génération d'un email de résumé consolidé
5. **Envoi** : Expédition du résumé à l'utilisateur
6. **Marquage** : Marquer comme lus les emails traités

### Processus Manuel
- Interface web ou CLI pour déclencher le processus à la demande
- Possibilité de personnaliser les filtres et paramètres

## 🔧 Configuration Requise

### APIs et Accès
- **Gmail API** : Credentials OAuth2 pour 3 comptes
- **Microsoft Graph API** : Credentials pour Hotmail
- **OpenAI API** : Clé pour la génération de résumés

### Permissions
- Lecture des emails
- Modification du statut "lu/non-lu"
- Envoi d'emails (pour le résumé)

## 📁 Structure du Projet (Prévue)

```
newsletters-manager/
├── src/
│   ├── agents/
│   │   ├── email_collector.py
│   │   ├── newsletter_detector.py
│   │   ├── content_summarizer.py
│   │   ├── scheduler.py
│   │   └── interface.py
│   ├── services/
│   │   ├── gmail_service.py
│   │   ├── outlook_service.py
│   │   └── ai_service.py
│   ├── models/
│   ├── utils/
│   └── config/
├── tests/
├── docs/
├── requirements.txt
├── docker-compose.yml (optionnel)
└── README.md
```

## 🎯 Objectifs de Développement

### Phase 1 : MVP
- [x] Connexion à une boîte Gmail
- [ ] Détection basique de newsletters
- [ ] Résumé simple avec IA
- [ ] Déclenchement manuel

### Phase 2 : Multi-comptes
- [ ] Intégration des 4 boîtes email
- [ ] Amélioration de la détection
- [ ] Scheduling automatique

### Phase 3 : Intelligence
- [ ] Architecture multi-agents A2A complète
- [ ] Interface web
- [ ] Personnalisation avancée
- [ ] Analytics et reporting

## 🚦 Getting Started

*Instructions détaillées à venir une fois le développement commencé*

## 📝 Notes de Développement

- Optimisé pour Apple Silicon (M2)
- Focus sur la simplicité et la fiabilité
- Respect des limites d'API des fournisseurs email
- Considérations de sécurité pour les credentials
- Logs détaillés pour le debugging

## 📄 License

Projet personnel - Usage privé uniquement 