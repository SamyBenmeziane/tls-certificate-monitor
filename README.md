# TLS Certificate Monitor

Outil en Python qui surveille les certificats HTTPS d'une liste de sites et signale ceux qui arrivent bientôt à expiration.

> Projet personnel en cours de développement. L'avancement est détaillé plus bas.

## Pourquoi ce projet

Quand un certificat TLS expire, le navigateur affiche une alerte de sécurité et la plupart des visiteurs ne vont pas plus loin. C'est un incident courant, même dans de grandes entreprises, et il vient presque toujours d'un renouvellement oublié.

Quand on gère quelques sites, on peut suivre les dates à la main. Quand on en gère des dizaines, il faut un outil. J'ai voulu en construire un simple, pour deux raisons : avoir quelque chose d'utile, et comprendre en détail ce qui se passe lors d'une connexion HTTPS, de la résolution DNS jusqu'à la vérification du certificat.

## Fonctionnement

Pour chaque site de la liste, le script :

1. résout le nom de domaine et ouvre une connexion TCP sur le port 443
2. établit une connexion TLS, comme le ferait un navigateur
3. récupère le certificat présenté par le serveur
4. en extrait les informations utiles : domaine, émetteur, dates de validité
5. calcule le nombre de jours avant l'expiration et en déduit un état

| État | Condition |
|---|---|
| OK | plus de 30 jours avant l'expiration |
| À surveiller | entre 7 et 30 jours |
| Critique | moins de 7 jours, ou certificat déjà expiré |
| Erreur | site injoignable, délai dépassé ou certificat invalide |

Exemple de sortie visée :

```
Domaine          Émetteur        Expiration   Jours   État
example.org      DigiCert        2027-02-18   136     OK
monsite.fr       Let's Encrypt   2026-10-29   21      À surveiller
ancien-site.com  -               -            -       Erreur (timeout)
```

## Structure du projet

### V1 — Moteur Python et interface CLI

Structure actuelle : les fichiers de code sont encore vides.

```text
tls-certificate-monitor/
├── core/                     moteur indépendant de Django
│   ├── tls_client.py         connexion TLS et récupération du certificat
│   ├── analyzer.py           calcul des jours restants et attribution du statut
│   └── cli.py                interface en ligne de commande et export CSV
├── tests/                    tests automatisés sans connexion réseau
│   └── test_analyzer.py      tests des dates et des statuts
├── domains.txt               liste des domaines à vérifier
└── README.md                 présentation et utilisation du projet
```

La partie réseau (`tls_client.py`) est séparée de l'analyse (`analyzer.py`).
Cela permet de tester l'analyse sans connexion réseau et de réutiliser
le moteur dans la future interface web.

### V2 — Interface web Django (prévue)

Structure prévue : les fichiers Django seront ajoutés après la V1.

```text
tls-certificate-monitor/
├── core/                     moteur Python réutilisé depuis la V1
│   ├── tls_client.py         connexion TLS et récupération du certificat
│   ├── analyzer.py           calcul des jours restants et attribution du statut
│   └── cli.py                interface en ligne de commande et export CSV
├── monitor/                  configuration Django : paramètres et routes
├── accounts/                 inscription et connexion avec l'authentification Django
├── certificates/             gestion des sites et des vérifications
│   ├── models.py             modèles Site et Verification, historique
│   ├── views.py              gestion des sites, vérification manuelle, export CSV
│   ├── alerts.py             alertes mail lors d'un changement de statut
│   ├── management/
│   │   └── commands/
│   │       └── check_certificates.py   vérifications automatiques lancées par cron
│   └── templates/            pages HTML de l'application
├── tests/                    tests du moteur Python
│   └── test_analyzer.py      tests des dates et des statuts
├── domains.txt               liste des domaines pour la CLI
├── manage.py                 commandes Django
├── requirements.txt          dépendances du projet
└── README.md                 présentation et utilisation du projet
```
## Utilisation prévue

Le script n'est pas encore utilisable dans cette forme. Une fois terminé :

```bash
python -m core.cli domains.txt
python -m core.cli domains.txt --csv rapport.csv
```

La V1 n’utilise que la bibliothèque standard de Python (`socket`, `ssl`, `datetime`, `csv`). Aucune installation supplémentaire n'est nécessaire.

## Avancement

Version 1, le moteur en ligne de commande :

- [x] Révision des bases : DNS, TCP, port 443, handshake TLS, chaîne de certification
- [x] Lecture de certificats à la main avec `openssl s_client` et `openssl x509`
- [x] Récupération du certificat d'un site en Python
- [ ] Calcul des jours restants et attribution d'un état
- [ ] Analyse d'une liste de sites depuis `domains.txt`
- [ ] Gestion des erreurs : domaine inexistant, timeout, certificat invalide
- [ ] Export CSV
- [ ] Tests unitaires

## Pour la suite

Une fois le moteur terminé, j'aimerais en faire une application web avec Django. C'est la version 2, que je ferai après la première.

### Ce que ça permettra

- créer un compte et se connecter
- ajouter ses propres sites à surveiller
- vérifier un site à la demande avec un bouton à côté de chacun
- activer une vérification automatique pour chaque site
- recevoir un mail quand un certificat passe à « à surveiller » ou « critique »
- consulter l'historique des vérifications et exporter le tout en CSV

### Deux façons de vérifier

```
  Bouton « Vérifier »                    Cron (vérification automatique)
  un site, tout de suite                 tous les sites dus, tous les comptes
           |                                          |
           v                                          v
   1 connexion TLS                      pool de threads (nombre limité)
           |                             un site par thread, avec un timeout
           |                                          |
           +------------------+-----------------------+
                              v
                  moteur `core` (le même dans les deux cas)
                              |
                              v
                 enregistrement de la vérification
                              |
                              v
        mail si l'état a changé (OK -> à surveiller -> critique)
```

Pour une vérification à la demande, il n'y a qu'un seul site à tester : des threads n'apporteraient rien. Pour le cron, en revanche, il y aura les sites de plusieurs comptes à vérifier d'un coup. Comme le script passe l'essentiel de son temps à attendre les serveurs, je les vérifierai en parallèle avec un pool de threads, avec un nombre limité de threads et un délai maximum par site pour qu'un serveur lent ne bloque pas les autres.

Quelques choix prévus :

- le mail n'est envoyé que quand l'état change, pas à chaque passage du cron, pour ne pas envoyer le même message toutes les heures
- l'enregistrement en base se fait une fois les threads terminés, pas à l'intérieur
- la commande lancée par cron sera protégée contre le chevauchement : si une exécution est encore en cours, la suivante ne démarre pas

### Structure prévue

```
tls-certificate-monitor/
├── core/                  le moteur de la version 1, réutilisé tel quel
├── monitor/               configuration Django
├── accounts/              inscription et connexion
├── certificates/
│   ├── models.py          Site et Verification
│   ├── views.py           liste des sites, ajout, bouton « Vérifier », export CSV
│   ├── alerts.py          envoi des mails
│   └── management/commands/check_certificates.py    lancée par cron
└── templates/
```

## Limites

- l'outil vérifie le certificat présenté par le serveur, pas toute la configuration TLS (versions de protocole, suites de chiffrement)
- prévu pour des listes de taille raisonnable, les sites sont analysés un par un

## Usage responsable

Le script se contente d'une connexion HTTPS standard, identique à celle d'un navigateur. Il ne cherche pas de failles et n'envoie rien d'inhabituel au serveur.

## Auteur

Samy Benmeziane, Master 1 Réseaux (RES) à Sorbonne Université.
[LinkedIn](https://www.linkedin.com/in/samy-benmeziane)
