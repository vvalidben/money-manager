"""French translations: English text (a ``str.format`` template) -> French.

Generated from the interface text; ``tests/test_i18n.py`` checks that every text
has a translation with the same placeholders."""

CATALOG: dict[str, str] = {
    "\n(to date)":
        "\n(à ce jour)",
    "\nLoans: {0}":
        "\nPrêts : {0}",
    "\n… and {0} more.":
        "\n… et {0} de plus.",
    " (out of date)":
        " (pas à jour)",
    " (protected by your password)":
        " (protégée par votre mot de passe)",
    " (the transaction type decides whether money comes in or goes out)":
        " (le type d'opération indique si l'argent entre ou sort)",
    " (to date)":
        " (à ce jour)",
    " ({0} of average monthly spending)":
        " ({0} de la dépense mensuelle moyenne)",
    " ({0}, newer vs older half)":
        " ({0}, moitié récente contre moitié ancienne)",
    " Add an Anthropic API key in Settings first.":
        " Ajoutez d'abord une clé API Anthropic dans les Paramètres.",
    " Its expense will be deleted too and your balance recalculated.":
        " Sa dépense sera supprimée aussi et votre solde recalculé.",
    " · adjustments and transfers {0}":
        " · ajustements et virements {0}",
    " · showing the first {0} lines":
        " · affichage des {0} premières lignes",
    " · The answer was cut off at the length limit.":
        " · La réponse a été coupée à la longueur maximale.",
    " · {0} overdue":
        " · {0} en retard",
    " · {0} sorted by your category rules":
        " · {0} classées par vos règles de catégorie",
    "! Behind":
        "! En retard sur le rythme",
    "! Needs attention":
        "! À surveiller",
    "! Overdue":
        "! Échéance dépassée",
    "'{0}' has more than two decimals":
        "« {0} » a plus de deux décimales",
    "'{0}' is ambiguous: write 1200 or 1 200 for thousands, or 1.20 for decimals.":
        "« {0} » est ambigu : écrivez 1200 ou 1 200 pour les milliers, ou 1,20 pour les décimales.",
    "'{0}' is an income category; subscriptions need an expense category.":
        "« {0} » est une catégorie de revenus ; les abonnements ont besoin d'une catégorie de dépenses.",
    "'{0}' is an {1} category and cannot be used for an {2} transaction.":
        "« {0} » est une catégorie de {1} et ne peut pas servir pour une opération de {2}.",
    "'{0}' is archived; restore it first.":
        "« {0} » est archivé ; restaurez-le d'abord.",
    "'{0}' is not a date.":
        "« {0} » n'est pas une date.",
    "'{0}' is not a valid amount.":
        "« {0} » n'est pas un montant valide.",
    "'{0}' is not an amount":
        "« {0} » n'est pas un montant",
    "'{0}' is not an investment category. Mark it as one (Statistics → Investment categories) or choose another.":
        "« {0} » n'est pas une catégorie d'investissement. Marquez-la comme telle (Statistiques → Catégories d'investissement) ou choisissez-en une autre.",
    "'{0}' is not an {1} category.":
        "« {0} » n'est pas une catégorie de {1}.",
    "'{0}' is paused; resume it first.":
        "« {0} » est en pause ; réactivez-le d'abord.",
    "'{0}' is reserved for money that is not allocated.":
        "« {0} » est réservé à l'argent qui n'est pas mis de côté.",
    "'{0}.{1}' has a value of the wrong type.":
        "« {0}.{1} » a une valeur du mauvais type.",
    "'{0}.{1}' is missing a value.":
        "« {0}.{1} » n'a pas de valeur.",
    "(no description)":
        "(sans description)",
    "(processed on this computer).":
        "(traité sur cet ordinateur).",
    "(sent to Anthropic).":
        "(envoyé à Anthropic).",
    "(to date)":
        "(à ce jour)",
    "0.00 (optional)":
        "0,00 (facultatif)",
    "1 receipt attached":
        "1 reçu joint",
    "1 recorded":
        "1 enregistrée",
    "1 recurring entry recorded":
        "1 opération récurrente enregistrée",
    "1 year":
        "1 an",
    "12/31/2026 (month first)":
        "12/31/2026 (mois d'abord)",
    "3 months":
        "3 mois",
    "30 days":
        "30 jours",
    "6 months":
        "6 mois",
    "7 days":
        "7 jours",
    "A backup contains all of your data: accounts, transactions, allocations, goals, subscriptions, investments, settings and the AI insight history. It is a readable JSON file that restores everything exactly. API keys are never included.":
        "Une sauvegarde contient toutes vos données : comptes, opérations, enveloppes, objectifs, abonnements, investissements, paramètres et l'historique des analyses d'IA. C'est un fichier JSON lisible qui restaure tout à l'identique. Les clés API n'y figurent jamais.",
    "A custom range has no preset dates.":
        "Une période personnalisée n'a pas de dates prédéfinies.",
    "A goal named '{0}' already exists.":
        "Un objectif nommé « {0} » existe déjà.",
    "A key ending in {0} is stored in {1}.":
        "Une clé se terminant par {0} est enregistrée dans {1}.",
    "A local model must run on this computer (localhost or 127.0.0.1). Use the online provider for remote services.":
        "Un modèle local doit fonctionner sur cet ordinateur (localhost ou 127.0.0.1). Utilisez le fournisseur en ligne pour les services distants.",
    "A recurring entry could not be recorded":
        "Une opération récurrente n'a pas pu être enregistrée",
    "A repayment cannot be dated before the debt started.":
        "Un remboursement ne peut pas être daté d'avant le début de la dette.",
    "a row in '{0}' is malformed.":
        "une ligne de « {0} » est mal formée.",
    "A safety backup was saved to:\n{0}":
        "Une sauvegarde de sécurité a été enregistrée dans :\n{0}",
    "A single {0} expense of {1} on {2} is {3}x the typical expense of {4}.":
        "Une dépense {0} de {1} le {2} représente {3}x la dépense habituelle de {4}.",
    "A subscription is a reminder: payments are only recorded when you confirm them, so your balance never changes on its own.":
        "Un abonnement est un rappel : les paiements ne sont enregistrés que lorsque vous les confirmez, donc votre solde ne change jamais tout seul.",
    "A subscription named '{0}' already exists.":
        "Un abonnement nommé « {0} » existe déjà.",
    "A transaction can have at most {0} receipts.":
        "Une opération peut avoir au plus {0} reçus.",
    "A transfer moves money between two of your accounts. Add the other account first (New account), e.g. your cash or a card.":
        "Un virement déplace de l'argent entre deux de vos comptes. Ajoutez d'abord l'autre compte (Nouveau compte), par ex. vos espèces ou une carte.",
    "A withdrawal lowers the amount invested. It does not change your balance: if the money came back to one of your accounts, record that as a transaction too.":
        "Un retrait diminue le montant investi. Il ne change pas votre solde : si l'argent est revenu sur l'un de vos comptes, enregistrez-le aussi comme une opération.",
    "About Money Manager":
        "À propos de Money Manager",
    "About {0} per month in {1} {2} (detected from the last 12 months)":
        "Environ {0} par mois pour {1} {2} (détectées sur les 12 derniers mois)",
    "Account":
        "Compte",
    "Account '{0}' uses {1}; allocations are kept in {2}.":
        "Le compte « {0} » utilise {1} ; les enveloppes sont tenues en {2}.",
    "Account '{0}' uses {1}; the {2} reports in {3}.":
        "Le compte « {0} » utilise {1} ; {2} est établi en {3}.",
    "Account created":
        "Compte créé",
    "Account deleted":
        "Compte supprimé",
    "Account updated":
        "Compte modifié",
    "Account {0!r} does not exist.":
        "Le compte {0!r} n'existe pas.",
    "Accounts":
        "Comptes",
    "Accounts below zero (e.g. cards)":
        "Comptes à découvert (ex. cartes)",
    "Accounts in credit":
        "Comptes créditeurs",
    "Across all budgets":
        "Sur l'ensemble des budgets",
    "Active":
        "Active",
    "Active goals":
        "Objectifs en cours",
    "Active subscriptions":
        "Abonnements actifs",
    "Active subscriptions only":
        "Abonnements actifs uniquement",
    "Actual balance today":
        "Solde réel aujourd'hui",
    "Add a second account":
        "Ajoutez un deuxième compte",
    "Add a second account (New account) to transfer between them":
        "Ajoutez un deuxième compte (Nouveau compte) pour faire des virements entre eux",
    "Add another account, e.g. cash or a card":
        "Ajouter un autre compte, par ex. espèces ou carte",
    "Add contribution":
        "Ajouter un versement",
    "Add investment":
        "Ajouter un investissement",
    "Add money":
        "Ajouter de l'argent",
    "Add money to {0}":
        "Ajouter de l'argent à {0}",
    "Add Netflix, your phone plan, internet or any other regular payment to see what they cost per month and when the next ones are due.":
        "Ajoutez Netflix, votre forfait téléphone, Internet ou tout autre paiement régulier pour voir ce qu'ils coûtent par mois et quand tombent les prochains.",
    "Add rule":
        "Ajouter une règle",
    "Add rule…":
        "Ajouter une règle…",
    "Add subscription":
        "Ajouter un abonnement",
    "Add the account you want to track first.":
        "Ajoutez d'abord le compte que vous voulez suivre.",
    "Add transaction":
        "Ajouter une opération",
    "Add transaction (Ctrl+N)":
        "Ajouter une opération (Ctrl+N)",
    "Add…":
        "Ajouter…",
    "Adjustment (+)":
        "Ajustement (+)",
    "Adjustment (−)":
        "Ajustement (−)",
    "Adjustments":
        "Ajustements",
    "Advisor answer":
        "Réponse du conseiller",
    "AES-256 encryption. Without the password the backup cannot be opened — a forgotten password cannot be recovered.":
        "Chiffrement AES-256. Sans le mot de passe, la sauvegarde ne peut pas être ouverte — un mot de passe oublié ne peut pas être récupéré.",
    "After 1 minute without use":
        "Après 1 minute d'inactivité",
    "After {0} minutes without use":
        "Après {0} minutes d'inactivité",
    "AI Advisor":
        "Conseiller IA",
    "AI answers interpret the figures calculated above and can be wrong. Numbers in the answer are checked against your data; check anything important yourself.":
        "Les réponses de l'IA interprètent les chiffres calculés ci-dessus et peuvent se tromper. Les nombres de la réponse sont vérifiés par rapport à vos données ; vérifiez vous-même tout ce qui est important.",
    "AI assistant":
        "Assistant IA",
    "AI features are off.":
        "Les fonctions d'IA sont désactivées.",
    "AI features are optional and off unless you choose a provider. They receive a summary calculated by Money Manager, never your database, transaction descriptions or account names.":
        "Les fonctions d'IA sont facultatives et désactivées tant que vous ne choisissez pas de fournisseur. Elles reçoivent un résumé calculé par Money Manager, jamais votre base de données, les descriptions des opérations ou les noms des comptes.",
    "AI insights are optional":
        "Les analyses par IA sont facultatives",
    "AI is off. Choose a local or online provider above; the summary works without AI.":
        "L'IA est désactivée. Choisissez un fournisseur local ou en ligne ci-dessus ; le résumé fonctionne sans IA.",
    "AI is off. The financial summary below is calculated by Money Manager without AI; choose a local or online provider to get AI insights.":
        "L'IA est désactivée. Le résumé financier ci-dessous est calculé par Money Manager sans IA ; choisissez un fournisseur local ou en ligne pour obtenir des analyses par l'IA.",
    "AI provider":
        "Fournisseur d'IA",
    "AI settings saved.":
        "Paramètres de l'IA enregistrés.",
    "AI settings…":
        "Paramètres de l'IA…",
    "All accounts":
        "Tous les comptes",
    "All accounts together":
        "Tous les comptes réunis",
    "All amounts use one currency: currently {0} (the default is {1}). It can be changed until the first account is created. Money Manager never converts between currencies and uses no exchange rates.":
        "Tous les montants utilisent une seule devise : actuellement {0} (par défaut {1}). Elle peut être changée jusqu'à la création du premier compte. Money Manager ne convertit jamais entre devises et n'utilise aucun taux de change.",
    "All categories":
        "Toutes les catégories",
    "All data was deleted.":
        "Toutes les données ont été supprimées.",
    "All files":
        "Tous les fichiers",
    "All subscriptions":
        "Tous les abonnements",
    "All time":
        "Depuis toujours",
    "all time":
        "depuis toujours",
    "All types":
        "Tous les types",
    "Allocated":
        "Mis de côté",
    "Allocation":
        "Enveloppe",
    "Allocation archived":
        "Enveloppe archivée",
    "Allocation created":
        "Enveloppe créée",
    "Allocation renamed":
        "Enveloppe renommée",
    "Allocation restored":
        "Enveloppe restaurée",
    "Allocation {0!r} does not exist.":
        "L'enveloppe {0!r} n'existe pas.",
    "Allocations":
        "Enveloppes",
    "Allocations exceed the real balance by {0}; move money from an allocation back to Available.":
        "Les enveloppes dépassent le solde réel de {0} ; remettez de l'argent d'une enveloppe dans Disponible.",
    "Allocations organise the money you already have: set some aside for bills, a holiday or an emergency fund. It stays in your accounts, but is no longer counted as Available to spend. Goals keep their money in allocations too.":
        "Les enveloppes organisent l'argent que vous avez déjà : mettez-en de côté pour les factures, des vacances ou une épargne de précaution. Il reste sur vos comptes, mais n'est plus compté comme Disponible. Les objectifs gardent aussi leur argent dans des enveloppes.",
    "Already recorded":
        "Déjà enregistrée",
    "Also remove the saved Anthropic API key":
        "Supprimer aussi la clé API Anthropic enregistrée",
    "Amount":
        "Montant",
    "Amount ({0})":
        "Montant ({0})",
    "Amount can have at most {0} decimal places.":
        "Le montant peut avoir au plus {0} décimales.",
    "Amount column":
        "Colonne du montant",
    "Amount must be a finite number.":
        "Le montant doit être un nombre fini.",
    "Amount must be a number.":
        "Le montant doit être un nombre.",
    "Amount must be greater than zero{0}.":
        "Le montant doit être supérieur à zéro{0}.",
    "Amount must not exceed {0:,} in size.":
        "Le montant ne doit pas dépasser {0:,}.",
    "Amount paid ({0})":
        "Montant payé ({0})",
    "Amount saved so far":
        "Montant épargné jusqu'ici",
    "Amounts":
        "Montants",
    "Amounts must not be floats; use a Decimal or a string such as '12.50'.":
        "Les montants ne doivent pas être des nombres flottants ; utilisez un Decimal ou un texte comme « 12.50 ».",
    "An account is where your money is kept, such as a bank account or cash. Enter its balance on the day you start tracking; earlier activity is already included in that balance.":
        "Un compte est l'endroit où se trouve votre argent, comme un compte bancaire ou des espèces. Saisissez son solde le jour où vous commencez le suivi ; l'activité antérieure est déjà incluse dans ce solde.",
    "An account is where your money is kept: a bank account, your cash wallet or a card. Add the first one with the balance it has today.":
        "Un compte est l'endroit où se trouve votre argent : un compte bancaire, votre porte-monnaie ou une carte. Ajoutez le premier avec son solde d'aujourd'hui.",
    "An account named '{0}' already exists.":
        "Un compte nommé « {0} » existe déjà.",
    "An allocation named '{0}' already exists.":
        "Une enveloppe nommée « {0} » existe déjà.",
    "An allocation sets money aside for a purpose, such as bills or a holiday. The money stays in your accounts; it is only no longer Available to spend.":
        "Une enveloppe met de l'argent de côté pour un usage précis, comme les factures ou des vacances. L'argent reste sur vos comptes ; il n'est simplement plus Disponible.",
    "An investment named '{0}' already exists.":
        "Un investissement nommé « {0} » existe déjà.",
    "An unexpected error occurred. Your data has not been sent anywhere; technical details were written to the log file.":
        "Une erreur inattendue s'est produite. Vos données n'ont été envoyées nulle part ; les détails techniques ont été écrits dans le fichier journal.",
    "an unknown date":
        "une date inconnue",
    "An {0} category named '{1}' already exists.":
        "Une catégorie de {0} nommée « {1} » existe déjà.",
    "Analyse":
        "Analyser",
    "Analyse with your local model":
        "Analyser avec votre modèle local",
    "Animations":
        "Animations",
    "Anthropic could not process the request: {0}":
        "Anthropic n'a pas pu traiter la demande : {0}",
    "Anthropic did not answer within {0} seconds.":
        "Anthropic n'a pas répondu dans les {0} secondes.",
    "Anthropic had a problem (HTTP {0}). Try again later.":
        "Anthropic a rencontré un problème (HTTP {0}). Réessayez plus tard.",
    "Anthropic is receiving too many requests. Try again in a minute.":
        "Anthropic reçoit trop de demandes. Réessayez dans une minute.",
    "Anthropic rejected the API key. Check it in Settings.":
        "Anthropic a refusé la clé API. Vérifiez-la dans les Paramètres.",
    "API key":
        "Clé API",
    "API key saved in {0}.":
        "Clé API enregistrée dans {0}.",
    "API keys are sensitive: anyone who has your key can use your Anthropic account at your cost. Money Manager keeps it in the Windows Credential Manager, never in the database, backups or logs. If you think it was exposed, remove it here and revoke it in the Anthropic Console.":
        "Les clés API sont sensibles : quiconque possède votre clé peut utiliser votre compte Anthropic à vos frais. Money Manager la garde dans le Gestionnaire d'identification Windows, jamais dans la base de données, les sauvegardes ou les journaux. Si vous pensez qu'elle a été exposée, supprimez-la ici et révoquez-la dans la console Anthropic.",
    "API keys cannot be serialised.":
        "Les clés API ne peuvent pas être sérialisées.",
    "App lock":
        "Verrouillage",
    "Appearance":
        "Apparence",
    "Apr":
        "avr.",
    "Archive":
        "Archiver",
    "Archive allocation":
        "Archiver l'enveloppe",
    "Archive {0}?\n\nIts {1} goes back to Available. You can restore the allocation later from the Archived list.":
        "Archiver {0} ?\n\nSes {1} retournent dans Disponible. Vous pourrez restaurer l'enveloppe plus tard depuis la liste des archives.",
    "Archived":
        "Archivées",
    "Ask":
        "Demander",
    "Ask about your finances, e.g. Why did my spending rise this month?":
        "Posez une question sur vos finances, ex. Pourquoi mes dépenses ont-elles augmenté ce mois-ci ?",
    "Ask again for the same period with your latest data.":
        "Redemander pour la même période avec vos données les plus récentes.",
    "Ask AI":
        "Demander à l'IA",
    "Ask for Windows Hello (PIN, fingerprint or face) when Money Manager opens and after a while without use. This keeps other people who use your computer out of the app; it does not encrypt the data file.":
        "Demander Windows Hello (code PIN, empreinte ou visage) à l'ouverture de Money Manager et après un moment d'inactivité. Cela empêche les autres personnes qui utilisent votre ordinateur d'accéder à l'application ; cela ne chiffre pas le fichier de données.",
    "Ask the advisor":
        "Interroger le conseiller",
    "Asking {0} ({1}) {2}…":
        "Question à {0} ({1}) {2}…",
    "At this pace: {0} by the end of the month":
        "À ce rythme : {0} à la fin du mois",
    "Attach a photo or PDF of the receipt":
        "Joindre une photo ou un PDF du reçu",
    "Attach a receipt":
        "Joindre un reçu",
    "Attach…":
        "Joindre…",
    "Aug":
        "août",
    "Automatic (local when available, otherwise online)":
        "Automatique (local si disponible, sinon en ligne)",
    "Automatic AI uses the local model when it is available. If it falls back to online AI, each request still needs your confirmation.":
        "L'IA automatique utilise le modèle local quand il est disponible. Si elle passe à l'IA en ligne, chaque demande nécessite toujours votre confirmation.",
    "Automatic uses the local model when Ollama is running with it, and otherwise the online provider. Online requests still show what would be sent and wait for your confirmation.":
        "Automatique utilise le modèle local quand Ollama fonctionne avec lui, et sinon le fournisseur en ligne. Les demandes en ligne montrent toujours ce qui serait envoyé et attendent votre confirmation.",
    "Automatic: uses {0}; otherwise the online provider ({1}) at {2}. Processing stays on this computer with the local model; online requests show what would be sent and wait for your confirmation.":
        "Automatique : utilise {0} ; sinon le fournisseur en ligne ({1}) sur {2}. Avec le modèle local, le traitement reste sur cet ordinateur ; les demandes en ligne montrent ce qui serait envoyé et attendent votre confirmation.",
    "Available":
        "Disponible",
    "Available (not allocated)":
        "Disponible (hors enveloppe)",
    "Available balance":
        "Solde disponible",
    "Average {0} per day":
        "En moyenne {0} par jour",
    "Backs the goal {0}":
        "Finance l'objectif {0}",
    "backup":
        "sauvegarde",
    "Backup saved and verified{0}: {1} records in {2}.":
        "Sauvegarde enregistrée et vérifiée{0} : {1} enregistrements dans {2}.",
    "Backups and CSV exports contain your data unencrypted. The AI insight history is stored locally and included in backups; clear it on the AI Advisor page.":
        "Les sauvegardes et exports CSV contiennent vos données non chiffrées. L'historique des analyses d'IA est stocké localement et inclus dans les sauvegardes ; effacez-le depuis la page Conseiller IA.",
    "Backups without a password and CSV exports contain your financial data unencrypted. Store them somewhere safe.":
        "Les sauvegardes sans mot de passe et les exports CSV contiennent vos données financières non chiffrées. Rangez-les en lieu sûr.",
    "Balance":
        "Solde",
    "Balance adjustments always affect Available money and cannot use an allocation.":
        "Les ajustements de solde concernent toujours l'argent Disponible et ne peuvent pas utiliser d'enveloppe.",
    "Balance adjustments do not use a category.":
        "Les ajustements de solde n'utilisent pas de catégorie.",
    "Balance already correct":
        "Le solde est déjà juste",
    "Balance and net worth on {0}":
        "Solde et patrimoine net au {0}",
    "Balance corrected":
        "Solde corrigé",
    "Balance correction":
        "Correction de solde",
    "Balance history":
        "Historique du solde",
    "Balance now {0}":
        "Solde actuel {0}",
    "Balance of your accounts":
        "Solde de vos comptes",
    "Balance on the start date ({0})":
        "Solde à la date de début ({0})",
    "Balance on {0}: {1}.":
        "Solde au {0} : {1}.",
    "Balance plus investment values at the end of each month":
        "Solde plus valeur des investissements à la fin de chaque mois",
    "Balance trend":
        "Évolution du solde",
    "Balance {0} + investments":
        "Solde {0} + investissements",
    "Balance ÷ average monthly spending (last 3 full months)":
        "Solde ÷ dépense mensuelle moyenne (3 derniers mois complets)",
    "Bank statements":
        "Relevés bancaires",
    "Before a reset":
        "Avant une réinitialisation",
    "Before importing a backup":
        "Avant l'import d'une sauvegarde",
    "Before restoring a safety copy":
        "Avant la restauration d'une copie de sécurité",
    "Behind or overdue":
        "En retard ou échus",
    "Best month: <b>{0}</b> ({1} kept). Hardest month: <b>{2}</b> ({3}).":
        "Meilleur mois : <b>{0}</b> ({1} gardés). Mois le plus difficile : <b>{2}</b> ({3}).",
    "Borrowed":
        "Emprunté",
    "Budget removed":
        "Budget supprimé",
    "Budget saved":
        "Budget enregistré",
    "Budget updated":
        "Budget modifié",
    "Budgets":
        "Budgets",
    "Budgets are for expense categories.":
        "Les budgets concernent les catégories de dépenses.",
    "Calculated by Money Manager's fixed rules — available with or without AI.":
        "Calculé par les règles fixes de Money Manager — disponible avec ou sans IA.",
    "Calendar months in the range":
        "Mois civils de la période",
    "Canadian dollar":
        "Dollar canadien",
    "Cancelled. Nothing was sent.":
        "Annulé. Rien n'a été envoyé.",
    "Cannot be longer than {0} characters.":
        "Ne peut pas dépasser {0} caractères.",
    "cannot be read":
        "illisible",
    "Cannot combine {0} and {1} amounts.":
        "Impossible de combiner des montants en {0} et en {1}.",
    "Cannot create the folder '{0}': {1}":
        "Impossible de créer le dossier « {0} » : {1}",
    "Cannot read the configuration file '{0}': {1}":
        "Impossible de lire le fichier de configuration « {0} » : {1}",
    "categories over budget":
        "catégories au-dessus du budget",
    "Category":
        "Catégorie",
    "Category breakdowns, balance trends and month-over-month comparisons will appear here.":
        "Les répartitions par catégorie, l'évolution du solde et les comparaisons d'un mois sur l'autre apparaîtront ici.",
    "Category changes":
        "Variations par catégorie",
    "Category name:":
        "Nom de la catégorie :",
    "category over budget":
        "catégorie au-dessus du budget",
    "Category rules":
        "Règles de catégorie",
    "Category {0!r} does not exist.":
        "La catégorie {0!r} n'existe pas.",
    "Category:":
        "Catégorie :",
    "Change":
        "Variation",
    "Change budget":
        "Modifier le budget",
    "Changes compare with {0} – {1}":
        "Les variations se comparent à {0} – {1}",
    "Chart":
        "Graphique",
    "Charts are on the way":
        "Les graphiques arrivent",
    "Check for a newer version once a day":
        "Rechercher une nouvelle version une fois par jour",
    "Check now":
        "Vérifier maintenant",
    "Checking…":
        "Vérification…",
    "Checks the provider without sending any financial data.":
        "Vérifie le fournisseur sans envoyer aucune donnée financière.",
    "Choose a category for spending and for income (or create one with New…). You can change categories of single entries later.":
        "Choisissez une catégorie pour les dépenses et une pour les revenus (ou créez-en une avec Nouvelle…). Vous pourrez changer la catégorie d'une opération plus tard.",
    "Choose a category, or create one with New….":
        "Choisissez une catégorie, ou créez-en une avec Nouvelle….",
    "Choose a category.":
        "Choisissez une catégorie.",
    "Choose a date range.":
        "Choisissez une période.",
    "Choose a file.":
        "Choisissez un fichier.",
    "Choose a local model in Settings first.":
        "Choisissez d'abord un modèle local dans les Paramètres.",
    "Choose a local model in the settings first.":
        "Choisissez d'abord un modèle local dans les paramètres.",
    "Choose a local or an online AI provider for insights. Your financial data is never sent online without your explicit confirmation.":
        "Choisissez un fournisseur d'IA local ou en ligne pour les analyses. Vos données financières ne sont jamais envoyées en ligne sans votre confirmation explicite.",
    "Choose a month between your first account and today.":
        "Choisissez un mois entre votre premier compte et aujourd'hui.",
    "Choose a password (at least {0} characters):":
        "Choisissez un mot de passe (au moins {0} caractères) :",
    "Choose a period of at most ten years.":
        "Choisissez une période de dix ans au plus.",
    "Choose a period.":
        "Choisissez une période.",
    "Choose a photo (JPG, PNG, WebP, GIF, BMP) or a PDF.":
        "Choisissez une photo (JPG, PNG, WebP, GIF, BMP) ou un PDF.",
    "Choose a range of at most ten years.":
        "Choisissez une période de dix ans au plus.",
    "Choose a year between your first account and today.":
        "Choisissez une année entre votre premier compte et aujourd'hui.",
    "Choose active or paused.":
        "Choisissez actif ou en pause.",
    "Choose an account if the money went out of it (or came into it): it is recorded as a balance adjustment, never as income or spending. Loans count in your net worth.":
        "Choisissez un compte si l'argent en est sorti (ou y est entré) : c'est enregistré comme un ajustement de solde, jamais comme un revenu ou une dépense. Les prêts comptent dans votre patrimoine net.",
    "Choose an account.":
        "Choisissez un compte.",
    "Choose an allocation.":
        "Choisissez une enveloppe.",
    "Choose an allocation; moving money from Available to Available does nothing.":
        "Choisissez une enveloppe ; déplacer de l'argent de Disponible vers Disponible ne change rien.",
    "Choose archived or active.":
        "Choisissez archivé ou actif.",
    "Choose dark, light or the Windows setting.":
        "Choisissez sombre, clair ou le réglage de Windows.",
    "Choose how AI features should work.":
        "Choisissez comment les fonctions d'IA doivent fonctionner.",
    "Choose how often it repeats.":
        "Choisissez la fréquence de répétition.",
    "Choose income or expense.":
        "Choisissez revenu ou dépense.",
    "Choose off, local, online or automatic.":
        "Choisissez désactivé, local, en ligne ou automatique.",
    "Choose one of the installed models.":
        "Choisissez l'un des modèles installés.",
    "Choose one of the offered languages.":
        "Choisissez l'une des langues proposées.",
    "Choose one of the offered lock times.":
        "Choisissez l'un des délais de verrouillage proposés.",
    "Choose one of the safety copies listed.":
        "Choisissez l'une des copies de sécurité de la liste.",
    "Choose one of the supported currencies.":
        "Choisissez l'une des devises proposées.",
    "Choose the account and check the columns. Lines already recorded in the account are skipped, so importing the same statement twice adds nothing.":
        "Choisissez le compte et vérifiez les colonnes. Les lignes déjà enregistrées dans le compte sont ignorées, donc importer deux fois le même relevé n'ajoute rien.",
    "Choose the account the payment was made from.":
        "Choisissez le compte qui a servi au paiement.",
    "Choose the investment category for the expense.":
        "Choisissez la catégorie d'investissement de la dépense.",
    "Choose two different accounts.":
        "Choisissez deux comptes différents.",
    "Choose what the advisor should do.":
        "Choisissez ce que le conseiller doit faire.",
    "Choose when paying":
        "Choisir lors du paiement",
    "Choose whether you lent or borrowed the money.":
        "Indiquez si vous avez prêté ou emprunté l'argent.",
    "Choose which local model to use.":
        "Choisissez le modèle local à utiliser.",
    "Choose yes or no.":
        "Choisissez oui ou non.",
    "Claude model":
        "Modèle Claude",
    "Clear filters":
        "Effacer les filtres",
    "Clear history":
        "Effacer l'historique",
    "Clear insight history":
        "Effacer l'historique des analyses",
    "Column {0}":
        "Colonne {0}",
    "Compared with this category's spending in the current calendar month.":
        "Comparé aux dépenses de cette catégorie pendant le mois en cours.",
    "Configuration file":
        "Fichier de configuration",
    "Configured: {0} at {1} (not contacted).":
        "Configuré : {0} sur {1} (non contacté).",
    "Confirm each payment when it happens: Record creates the expense, Skip moves on without one.":
        "Confirmez chaque paiement quand il a lieu : Enregistrer crée la dépense, Passer avance sans en créer.",
    "Confirm it's you with Windows Hello — your PIN, fingerprint or face.":
        "Confirmez votre identité avec Windows Hello — code PIN, empreinte ou visage.",
    "Confirm the earlier payment of this subscription first.":
        "Confirmez d'abord le paiement précédent de cet abonnement.",
    "Confirm with Windows Hello…":
        "Confirmez avec Windows Hello…",
    "Confirms the payment due {0} by recording one expense. The next payment will then be due {1}.":
        "Confirme le paiement dû le {0} en enregistrant une dépense. Le prochain paiement sera alors dû le {1}.",
    "Connected: {0} at {1}.":
        "Connecté : {0} sur {1}.",
    "Consent is only given by accepting a DataDisclosure.":
        "Le consentement ne peut être donné qu'en acceptant une divulgation (DataDisclosure).",
    "Contributed {0} · withdrawn {1}":
        "Versé {0} · retiré {1}",
    "Contribution":
        "Versement",
    "contribution":
        "versement",
    "Contributions & withdrawals":
        "Versements et retraits",
    "Correct balance":
        "Corriger le solde",
    "Correct balance…":
        "Corriger le solde…",
    "Correct the balance of {0}":
        "Corriger le solde de {0}",
    "Could not archive the allocation":
        "Impossible d'archiver l'enveloppe",
    "Could not compute statistics":
        "Impossible de calculer les statistiques",
    "Could not compute the summary":
        "Impossible de calculer le résumé",
    "Could not create category":
        "Impossible de créer la catégorie",
    "Could not delete goal":
        "Impossible de supprimer l'objectif",
    "Could not delete the account":
        "Impossible de supprimer le compte",
    "Could not delete the loan":
        "Impossible de supprimer le prêt",
    "Could not delete the transfer":
        "Impossible de supprimer le virement",
    "Could not delete transaction":
        "Impossible de supprimer l'opération",
    "Could not list the safety copies: {0}":
        "Impossible de lister les copies de sécurité : {0}",
    "Could not load accounts":
        "Impossible de charger les comptes",
    "Could not load allocations":
        "Impossible de charger les enveloppes",
    "Could not load budgets":
        "Impossible de charger les budgets",
    "Could not load goals":
        "Impossible de charger les objectifs",
    "Could not load investments":
        "Impossible de charger les investissements",
    "Could not load subscriptions":
        "Impossible de charger les abonnements",
    "Could not load the dashboard":
        "Impossible de charger le tableau de bord",
    "Could not load transactions":
        "Impossible de charger les opérations",
    "Could not prepare the report":
        "Impossible de préparer le rapport",
    "Could not reach the update server. Are you online?":
        "Impossible de joindre le serveur de mises à jour. Êtes-vous connecté à Internet ?",
    "Could not reach {0}. Check the internet connection.":
        "Impossible de joindre {0}. Vérifiez la connexion Internet.",
    "Could not read from the Windows Credential Manager.":
        "Impossible de lire le Gestionnaire d'identification Windows.",
    "Could not read the file: {0}":
        "Impossible de lire le fichier : {0}",
    "Could not read the statement":
        "Impossible de lire le relevé",
    "Could not remove the budget":
        "Impossible de supprimer le budget",
    "Could not remove the key from the Windows Credential Manager.":
        "Impossible de retirer la clé du Gestionnaire d'identification Windows.",
    "Could not remove the repayment":
        "Impossible de retirer le remboursement",
    "Could not rename the allocation":
        "Impossible de renommer l'enveloppe",
    "Could not restore the allocation":
        "Impossible de restaurer l'enveloppe",
    "Could not save the report":
        "Impossible d'enregistrer le rapport",
    "Could not save the setting":
        "Impossible d'enregistrer le paramètre",
    "Could not save to the Windows Credential Manager.":
        "Impossible d'enregistrer dans le Gestionnaire d'identification Windows.",
    "Could not undo the move":
        "Impossible d'annuler le mouvement",
    "Could not update the investment":
        "Impossible de modifier l'investissement",
    "Could not update the subscription":
        "Impossible de modifier l'abonnement",
    "Could not write the file: {0}":
        "Impossible d'écrire le fichier : {0}",
    "Create a budget":
        "Créer un budget",
    "Create a category first.":
        "Créez d'abord une catégorie.",
    "Create a goal such as an emergency fund, a trip or a new laptop. Keep its money in an allocation and track your progress towards the target.":
        "Créez un objectif comme une épargne de précaution, un voyage ou un nouvel ordinateur. Gardez son argent dans une enveloppe et suivez votre progression vers le montant visé.",
    "Create account":
        "Créer le compte",
    "Create allocation":
        "Créer l'enveloppe",
    "Create an account first":
        "Créez d'abord un compte",
    "Create an account first.":
        "Créez d'abord un compte.",
    "Create an account first; the report covers its months.":
        "Créez d'abord un compte ; le rapport couvre ses mois.",
    "Create an account first; the report covers its years.":
        "Créez d'abord un compte ; le rapport couvre ses années.",
    "Create an account to get started":
        "Créez un compte pour commencer",
    "Create an allocation":
        "Créer une enveloppe",
    "Create goal":
        "Créer l'objectif",
    "Create savings targets with deadlines and follow your progress.":
        "Créez des objectifs d'épargne avec échéance et suivez votre progression.",
    "Credit column (money in)":
        "Colonne crédit (entrées)",
    "Crypto":
        "Crypto",
    "Currency":
        "Devise",
    "Currency and appearance options will be added here.":
        "Les options de devise et d'apparence seront ajoutées ici.",
    "Currency must be a three-letter ISO 4217 code such as 'MAD'.":
        "La devise doit être un code ISO 4217 de trois lettres, comme « MAD ».",
    "Currency set to {0}.":
        "Devise définie sur {0}.",
    "Current value":
        "Valeur actuelle",
    "Current value ({0})":
        "Valeur actuelle ({0})",
    "Custom":
        "Personnalisée",
    "Custom range…":
        "Période personnalisée…",
    "Daily automatic copy":
        "Copie automatique quotidienne",
    "Daily copies":
        "Copies quotidiennes",
    "Dark":
        "Sombre",
    "Dashboard":
        "Tableau de bord",
    "Data folder":
        "Dossier des données",
    "Data schema":
        "Schéma de données",
    "Database created":
        "Base de données créée",
    "Database file":
        "Fichier de base de données",
    "Date":
        "Date",
    "Date cannot be before the account's opening date ({0}); the opening balance already includes earlier activity.":
        "La date ne peut pas précéder la date d'ouverture du compte ({0}) ; le solde d'ouverture inclut déjà l'activité antérieure.",
    "Date cannot be before {0}.":
        "La date ne peut pas être antérieure au {0}.",
    "Date cannot be in the future.":
        "La date ne peut pas être dans le futur.",
    "Date column":
        "Colonne de la date",
    "Date format":
        "Format de date",
    "day":
        "jour",
    "days":
        "jours",
    "Deadline":
        "Échéance",
    "Debit column (money out)":
        "Colonne débit (sorties)",
    "Debt {0!r} does not exist.":
        "La dette {0!r} n'existe pas.",
    "Dec":
        "déc.",
    "Decrease":
        "Diminuer",
    "Delete":
        "Supprimer",
    "Delete account":
        "Supprimer le compte",
    "Delete all data":
        "Supprimer toutes les données",
    "Delete all of your data?":
        "Supprimer toutes vos données ?",
    "Delete entry":
        "Supprimer l'écriture",
    "Delete every stored AI answer? Your financial data is not affected.":
        "Supprimer toutes les réponses d'IA enregistrées ? Vos données financières ne sont pas touchées.",
    "Delete goal":
        "Supprimer l'objectif",
    "Delete investment":
        "Supprimer l'investissement",
    "Delete loan":
        "Supprimer le prêt",
    "Delete recurring entry":
        "Supprimer l'opération récurrente",
    "Delete selected":
        "Supprimer la sélection",
    "Delete subscription":
        "Supprimer l'abonnement",
    "Delete the account {0}?\n\nOnly an account without any transactions can be deleted. This cannot be undone.":
        "Supprimer le compte {0} ?\n\nSeul un compte sans aucune opération peut être supprimé. Cette action est irréversible.",
    "Delete the goal “{0}”? Its money stays in your balance either way.":
        "Supprimer l'objectif « {0} » ? Son argent reste de toute façon dans votre solde.",
    "Delete the goal “{0}”? This cannot be undone.":
        "Supprimer l'objectif « {0} » ? Cette action est irréversible.",
    "Delete the subscription “{0}”? Expenses already recorded for it stay in your transactions.":
        "Supprimer l'abonnement « {0} » ? Les dépenses déjà enregistrées pour lui restent dans vos opérations.",
    "Delete this transaction?\n\n{0} · {1} · {2}\n\nYour balance will be recalculated. This cannot be undone.":
        "Supprimer cette opération ?\n\n{0} · {1} · {2}\n\nVotre solde sera recalculé. Cette action est irréversible.",
    "Delete this transfer?\n\n{0} · {1} · {2}\n\nBoth sides are removed and both balances are recalculated. This cannot be undone.":
        "Supprimer ce virement ?\n\n{0} · {1} · {2}\n\nLes deux côtés sont retirés et les deux soldes recalculés. Cette action est irréversible.",
    "Delete this value?":
        "Supprimer cette valeur ?",
    "Delete this {0}?{1}":
        "Supprimer ce {0} ?{1}",
    "Delete transaction":
        "Supprimer l'opération",
    "Delete transfer":
        "Supprimer le virement",
    "Delete value":
        "Supprimer la valeur",
    "Delete “{0}” and its history? Expenses already recorded for its contributions stay in your transactions.":
        "Supprimer « {0} » et son historique ? Les dépenses déjà enregistrées pour ses versements restent dans vos opérations.",
    "Delete “{0}” and its repayments? Money already moved through your accounts stays recorded.":
        "Supprimer « {0} » et ses remboursements ? L'argent déjà passé par vos comptes reste enregistré.",
    "Deletes every account, transaction, allocation, goal, subscription, investment, setting and AI insight. A safety backup of the database is written first. This cannot be undone from inside the app.":
        "Supprime tous les comptes, opérations, enveloppes, objectifs, abonnements, investissements, paramètres et analyses d'IA. Une sauvegarde de sécurité de la base de données est d'abord écrite. Cette action ne peut pas être annulée depuis l'application.",
    "Deleting a contribution paid from your accounts also deletes its expense.":
        "Supprimer un versement payé depuis vos comptes supprime aussi sa dépense.",
    "Description":
        "Description",
    "Description column":
        "Colonne de la description",
    "Destination: {0} ({1}) · model {2}":
        "Destination : {0} ({1}) · modèle {2}",
    "Download…":
        "Télécharger…",
    "Due by":
        "À rembourser avant le",
    "Due in the next {0} days":
        "À payer dans les {0} prochains jours",
    "Due today":
        "À payer aujourd'hui",
    "Due {0}":
        "Échéance le {0}",
    "Duplicate navigation key: {0!r}":
        "Clé de navigation en double : {0!r}",
    "e.g. Bank account":
        "ex. Compte bancaire",
    "e.g. Bills, Holiday, Emergency fund":
        "ex. Factures, Vacances, Épargne de précaution",
    "e.g. Emergency Fund":
        "ex. Épargne de précaution",
    "e.g. Groceries at Marjane":
        "ex. Courses chez Marjane",
    "e.g. llama3.2":
        "ex. llama3.2",
    "e.g. MSCI World ETF":
        "ex. ETF MSCI World",
    "e.g. Netflix":
        "ex. Netflix",
    "e.g. Rent, Salary":
        "ex. Loyer, Salaire",
    "e.g. Sami, Car loan":
        "ex. Sami, Crédit auto",
    "Edit":
        "Modifier",
    "Edit account":
        "Modifier le compte",
    "Edit goal":
        "Modifier l'objectif",
    "Edit investment":
        "Modifier l'investissement",
    "Edit loan":
        "Modifier le prêt",
    "Edit recurring entry":
        "Modifier l'opération récurrente",
    "Edit subscription":
        "Modifier l'abonnement",
    "Edit transaction":
        "Modifier l'opération",
    "Edit…":
        "Modifier…",
    "Emergency runway":
        "Réserve de sécurité",
    "Empty":
        "Vide",
    "Enter a keyword of 2 to 60 letters or digits.":
        "Saisissez un mot-clé de 2 à 60 lettres ou chiffres.",
    "Enter a model name.":
        "Saisissez un nom de modèle.",
    "Enter a valid calendar date.":
        "Saisissez une date valide.",
    "Enter an amount.":
        "Saisissez un montant.",
    "Enter an API key.":
        "Saisissez une clé API.",
    "Enter only the scheme, host and port of the local model.":
        "Saisissez uniquement le schéma, l'hôte et le port du modèle local.",
    "Enter the current value to see the profit or loss.":
        "Saisissez la valeur actuelle pour voir le gain ou la perte.",
    "Enter the timeout as a whole number of seconds.":
        "Saisissez le délai en nombre entier de secondes.",
    "Enter what the investment is worth, e.g. from your broker's app. A value entered for the same day replaces the earlier one.":
        "Saisissez ce que vaut l'investissement, par ex. depuis l'application de votre courtier. Une valeur saisie pour le même jour remplace la précédente.",
    "Entry added":
        "Opération ajoutée",
    "Entry deleted":
        "Opération supprimée",
    "Entry updated":
        "Opération modifiée",
    "Entry updated · rule learned":
        "Opération modifiée · règle apprise",
    "Entry {0!r} does not exist.":
        "L'écriture {0!r} n'existe pas.",
    "Euro":
        "Euro",
    "Every":
        "Tous les",
    "Every 3 months":
        "Tous les 3 mois",
    "Every 3 months, day {0}":
        "Tous les 3 mois, le {0}",
    "Every month":
        "Tous les mois",
    "Every week":
        "Toutes les semaines",
    "Every year":
        "Tous les ans",
    "Everything is on schedule":
        "Tout est dans les temps",
    "Everything within its limit":
        "Tout est dans les limites",
    "Exactly what will be sent:":
        "Exactement ce qui sera envoyé :",
    "Expense":
        "Dépense",
    "expense":
        "dépenses",
    "Expenses":
        "Dépenses",
    "Expenses in view":
        "Dépenses affichées",
    "Expenses this month":
        "Dépenses ce mois-ci",
    "Expenses · {0}":
        "Dépenses · {0}",
    "Export and import":
        "Exporter et importer",
    "Export backup":
        "Exporter une sauvegarde",
    "Export backup…":
        "Exporter une sauvegarde…",
    "Export transactions":
        "Exporter les opérations",
    "Export transactions (CSV)…":
        "Exporter les opérations (CSV)…",
    "External (not from your accounts)":
        "Extérieur (pas depuis vos comptes)",
    "External money (e.g. invested before you started tracking): your balance does not change.":
        "Argent extérieur (par ex. investi avant le début du suivi) : votre solde ne change pas.",
    "falling":
        "en baisse",
    "Feb":
        "févr.",
    "Filter by {0}":
        "Filtrer par {0}",
    "financial analysis":
        "analyse financière",
    "Financial health":
        "Santé financière",
    "Financial information about you will be sent over the internet to {0} ({1}) to generate the answer. It leaves this computer and is handled under {2}'s terms and data-retention policy. Money Manager sends only the summary shown below, never your database.":
        "Des informations financières vous concernant seront envoyées par Internet à {0} ({1}) pour produire la réponse. Elles quittent cet ordinateur et sont traitées selon les conditions et la politique de conservation des données de {2}. Money Manager n'envoie que le résumé ci-dessous, jamais votre base de données.",
    "Financial summary":
        "Résumé financier",
    "Find installed models":
        "Rechercher les modèles installés",
    "First date":
        "Première date",
    "Follow your contributions and holdings. Values are entered by you; no market data is fetched and no advice is given.":
        "Suivez vos versements et vos placements. Les valeurs sont saisies par vous ; aucune donnée de marché n'est récupérée et aucun conseil n'est donné.",
    "Frequency":
        "Fréquence",
    "Fridays":
        "le vendredi",
    "From":
        "De",
    "From <b>{0}</b> at the end of {1} to <b>{2}</b> on {3} ({4}).":
        "De <b>{0}</b> fin {1} à <b>{2}</b> le {3} ({4}).",
    "From account":
        "Depuis le compte",
    "From date":
        "Du",
    "From {0}":
        "Depuis {0}",
    "fully repaid":
        "entièrement remboursé",
    "Goal":
        "Objectif",
    "Goal contribution: {name}":
        "Versement vers l'objectif : {name}",
    "Goal not available":
        "Objectif indisponible",
    "Goal withdrawal: {name}":
        "Retrait de l'objectif : {name}",
    "Goal {0!r} does not exist.":
        "L'objectif {0!r} n'existe pas.",
    "Goals":
        "Objectifs",
    "Goals below their expected pace":
        "Objectifs en dessous du rythme prévu",
    "Goals keep their money in one":
        "Les objectifs gardent leur argent dans une enveloppe",
    "Goals on {0}":
        "Objectifs au {0}",
    "Gold":
        "Or",
    "Group thousands with spaces, e.g. 1 200 000.":
        "Séparez les milliers par des espaces, par ex. 1 200 000.",
    "Holdings":
        "Placements",
    "How your total balance is allocated":
        "Comment votre solde total est réparti",
    "I borrowed money (I owe it)":
        "J'ai emprunté de l'argent (je le dois)",
    "I lent money (someone owes me)":
        "J'ai prêté de l'argent (on me le doit)",
    "I understand that this information will leave my computer.":
        "Je comprends que ces informations vont quitter mon ordinateur.",
    "I'll track it manually (money outside the app)":
        "Je le suis moi-même (argent en dehors de l'application)",
    "Import 1 entry":
        "Importer 1 opération",
    "Import a bank statement (CSV file)":
        "Importer un relevé bancaire (fichier CSV)",
    "Import backup":
        "Importer une sauvegarde",
    "Import backup…":
        "Importer une sauvegarde…",
    "Import bank statement":
        "Importer un relevé bancaire",
    "Import complete":
        "Import terminé",
    "Import {0}":
        "Importer {0}",
    "Import {0} entries":
        "Importer {0} opérations",
    "imported":
        "importé",
    "Imported from a bank statement":
        "Importé d'un relevé bancaire",
    "Imported from {0}":
        "Importé de {0}",
    "Import…":
        "Importer…",
    "In a new allocation for this goal (recommended)":
        "Dans une nouvelle enveloppe pour cet objectif (recommandé)",
    "In an allocation I already have":
        "Dans une enveloppe que j'ai déjà",
    "In budgeted categories":
        "Dans les catégories budgétées",
    "in goals":
        "dans les objectifs",
    "In {0} allocation{1}":
        "Dans {0} enveloppe{1}",
    "In {0} days":
        "Dans {0} jours",
    "Included:\n":
        "Inclus :\n",
    "Income":
        "Revenus",
    "income":
        "revenus",
    "Income and expenses recorded automatically, e.g. salary or rent":
        "Revenus et dépenses enregistrés automatiquement, par ex. salaire ou loyer",
    "Income and expenses that repeat — salary, rent, savings — are recorded automatically on each date. Subscriptions you confirm one by one stay on the Subscriptions page.":
        "Les revenus et dépenses qui se répètent — salaire, loyer, épargne — sont enregistrés automatiquement à chaque date. Les abonnements que vous confirmez un par un restent sur la page Abonnements.",
    "Income goes to":
        "Les revenus vont dans",
    "Income in view":
        "Revenus affichés",
    "Income this month":
        "Revenus ce mois-ci",
    "Income vs expenses":
        "Revenus et dépenses",
    "Income · {0}":
        "Revenus · {0}",
    "Increase":
        "Augmenter",
    "Initial allocation":
        "Montant initial de l'enveloppe",
    "Insight history":
        "Historique des analyses",
    "Insights":
        "Analyses",
    "Into account":
        "Dans le compte",
    "Invalid category kind {0!r}; expected one of: {1}.":
        "Type de catégorie {0!r} non valide ; valeurs attendues : {1}.",
    "Invalid frequency {0!r}; expected one of: {1}.":
        "Fréquence {0!r} non valide ; valeurs attendues : {1}.",
    "Invalid investment type {0!r}; expected one of: {1}.":
        "Type d'investissement {0!r} non valide ; valeurs attendues : {1}.",
    "Invalid reference.":
        "Référence non valide.",
    "Invalid transaction type {0!r}; expected one of: {1}.":
        "Type d'opération {0!r} non valide ; valeurs attendues : {1}.",
    "Invested":
        "Investi",
    "Investment categories":
        "Catégories d'investissement",
    "Investment categories…":
        "Catégories d'investissement…",
    "Investment category":
        "Catégorie d'investissement",
    "Investment contribution":
        "Versement sur un investissement",
    "Investment contributions were {0}, {1} of income.":
        "Les investissements ont atteint {0}, soit {1} des revenus.",
    "Investment rate {0} of income":
        "Taux d'investissement {0} des revenus",
    "Investment {0!r} does not exist.":
        "L'investissement {0!r} n'existe pas.",
    "Investments":
        "Investissements",
    "Investments (latest values entered)":
        "Investissements (dernières valeurs saisies)",
    "Investments and loans":
        "Investissements et prêts",
    "Investments excluded · top 5, the rest as Other":
        "Investissements exclus · les 5 premières, le reste dans Autres",
    "it contains no tables.":
        "il ne contient aucune table.",
    "its tables do not match this version of Money Manager.":
        "ses tables ne correspondent pas à cette version de Money Manager.",
    "Jan":
        "janv.",
    "Jul":
        "juil.",
    "Jun":
        "juin",
    "Keep recurring payments under control.":
        "Gardez le contrôle de vos paiements récurrents.",
    "Keep the money in “{0}”":
        "Garder l'argent dans « {0} »",
    "Key facts":
        "Faits clés",
    "Keyword in the description:":
        "Mot-clé dans la description :",
    "Kind":
        "Type",
    "Language":
        "Langue",
    "Largest expenses":
        "Plus grosses dépenses",
    "Largest spending category: {0}, {1} ({2} of spending).":
        "Plus grande catégorie de dépenses : {0}, {1} ({2} des dépenses).",
    "Last 12 months":
        "12 derniers mois",
    "Last 3 months":
        "3 derniers mois",
    "Last 30 days":
        "30 derniers jours",
    "Last 6 months · adjustments excluded":
        "6 derniers mois · ajustements exclus",
    "Last month":
        "Le mois dernier",
    "Last paid":
        "Dernier paiement",
    "Last valued":
        "Dernière évaluation",
    "Last year":
        "L'année dernière",
    "Latest known values":
        "Dernières valeurs connues",
    "Left":
        "Reste",
    "Left to repay: {0}.":
        "Reste à rembourser : {0}.",
    "Left to spend":
        "Reste à dépenser",
    "Lent":
        "Prêté",
    "Light":
        "Clair",
    "Limit":
        "Limite",
    "Line":
        "Ligne",
    "Loan deleted":
        "Prêt supprimé",
    "Loan from {0}":
        "Emprunt auprès de {0}",
    "Loan recorded":
        "Prêt enregistré",
    "Loan to {0}":
        "Prêt à {0}",
    "Loan updated":
        "Prêt modifié",
    "Loans":
        "Prêts",
    "Loans (owed to you − you owe)":
        "Prêts (ce qu'on vous doit − ce que vous devez)",
    "Loans and debts":
        "Prêts et dettes",
    "Local":
        "Local",
    "Local AI (Ollama) processes the financial summary on this computer; nothing is sent over the internet.":
        "L'IA locale (Ollama) traite le résumé financier sur cet ordinateur ; rien n'est envoyé sur Internet.",
    "Local AI ({0} via Ollama): your financial summary is processed on this computer and is not sent over the internet.":
        "IA locale ({0} via Ollama) : votre résumé financier est traité sur cet ordinateur et n'est pas envoyé sur Internet.",
    "Local data storage":
        "Stockage local des données",
    "Local model":
        "Modèle local",
    "Local model (Ollama, on this computer)":
        "Modèle local (Ollama, sur cet ordinateur)",
    "Lock Money Manager with Windows Hello":
        "Verrouiller Money Manager avec Windows Hello",
    "Lock now":
        "Verrouiller maintenant",
    "Lock with Windows Hello":
        "Verrouiller avec Windows Hello",
    "Log files":
        "Fichiers journaux",
    "Made by Money Manager {0} on your computer from the entries you recorded. Amounts in {1}. Transfers between your accounts and balance corrections are not counted as income or spending.":
        "Établi par Money Manager {0} sur votre ordinateur à partir des opérations que vous avez enregistrées. Montants en {1}. Les virements entre vos comptes et les corrections de solde ne comptent ni comme revenus ni comme dépenses.",
    "Made by Money Manager {0} on your computer from the entries you recorded. Amounts in {1}. Transfers between your accounts, loans and balance corrections are not counted as income or spending.":
        "Établi par Money Manager {0} sur votre ordinateur à partir des opérations que vous avez enregistrées. Montants en {1}. Les virements entre vos comptes, les prêts et les corrections de solde ne comptent ni comme revenus ni comme dépenses.",
    "Mar":
        "mars",
    "Mark investment categories to track this":
        "Marquez des catégories d'investissement pour suivre ceci",
    "Match the balance your bank shows (recorded as an adjustment)":
        "Aligner sur le solde indiqué par votre banque (enregistré comme ajustement)",
    "May":
        "mai",
    "Measured from your own data by fixed rules — no AI, no judgements.":
        "Mesuré à partir de vos propres données par des règles fixes — sans IA, sans jugement.",
    "Mondays":
        "le lundi",
    "Money / Allocations":
        "Argent / Enveloppes",
    "Money kept in the allocation “{0}”":
        "Argent gardé dans l'enveloppe « {0} »",
    "Money kept in the allocation “{0}”.":
        "Argent gardé dans l'enveloppe « {0} ».",
    "Money Manager backup":
        "Sauvegarde Money Manager",
    "Money Manager is locked":
        "Money Manager est verrouillé",
    "Money Manager saves a copy of all your data before every reset, import or restore, before an update changes how data is stored, and once a day. Restoring a copy replaces your current data, which is itself saved first, so a restore can be undone the same way.":
        "Money Manager enregistre une copie de toutes vos données avant chaque réinitialisation, import ou restauration, avant qu'une mise à jour change la façon dont les données sont stockées, et une fois par jour. Restaurer une copie remplace vos données actuelles, elles-mêmes sauvegardées d'abord, donc une restauration peut être annulée de la même façon.",
    "Money Manager shows {0} today. Enter the balance your bank (or wallet) shows; the difference is recorded as a balance adjustment, so nothing is overwritten and you can see the correction in Transactions.":
        "Money Manager affiche {0} aujourd'hui. Saisissez le solde affiché par votre banque (ou votre porte-monnaie) ; la différence est enregistrée comme un ajustement de solde, donc rien n'est écrasé et la correction apparaît dans Opérations.",
    "Money Manager works fully offline. The only network connections it can make are to a local Ollama server and, when you confirm a request, to Anthropic's API.":
        "Money Manager fonctionne entièrement hors ligne. Les seules connexions réseau possibles sont vers un serveur Ollama local et, quand vous confirmez une demande, vers l'API d'Anthropic.",
    "Money Manager {0} is available":
        "Money Manager {0} est disponible",
    "MONEY MANAGER · MONTHLY REPORT":
        "MONEY MANAGER · RAPPORT MENSUEL",
    "MONEY MANAGER · YEARLY REPORT":
        "MONEY MANAGER · RAPPORT ANNUEL",
    "Money moved":
        "Argent déplacé",
    "Money moved in or out after the last value — update the value to see the current return.":
        "De l'argent est entré ou sorti après la dernière valeur — mettez la valeur à jour pour voir le rendement actuel.",
    "Money moved through":
        "Argent passé par",
    "Money organisation":
        "Organisation de l'argent",
    "Money that actually enters or leaves your accounts.":
        "L'argent qui entre réellement sur vos comptes ou en sort.",
    "Money you lent to someone or borrowed — a friend, a car loan. What is left counts in your net worth.":
        "L'argent que vous avez prêté à quelqu'un ou emprunté — un ami, un crédit auto. Ce qui reste compte dans votre patrimoine net.",
    "Month":
        "Mois",
    "Month by month":
        "Mois par mois",
    "Month-end balance":
        "Solde de fin de mois",
    "Month:":
        "Mois :",
    "Monthly":
        "Tous les mois",
    "Monthly comparison":
        "Comparaison mensuelle",
    "Monthly cost":
        "Coût mensuel",
    "Monthly cost by category":
        "Coût mensuel par catégorie",
    "Monthly limit":
        "Limite mensuelle",
    "Monthly limits per spending category, compared with this month so far.":
        "Limites mensuelles par catégorie de dépenses, comparées au mois en cours.",
    "Monthly report":
        "Rapport mensuel",
    "Monthly report…":
        "Rapport mensuel…",
    "Monthly summary":
        "Résumé du mois",
    "Monthly, day {0}":
        "Tous les mois, le {0}",
    "More is set aside than you have":
        "Plus d'argent est mis de côté que vous n'en avez",
    "More is set aside than you have: Available is short by {0}. Take money out of an allocation to fix it.":
        "Plus d'argent est mis de côté que vous n'en avez : il manque {0} dans Disponible. Retirez de l'argent d'une enveloppe pour corriger.",
    "More settings coming":
        "D'autres paramètres arrivent",
    "Moroccan dirham":
        "Dirham marocain",
    "Most expensive":
        "Le plus cher",
    "Move":
        "Déplacer",
    "Move from Available now · {0} available":
        "Prendre dans Disponible maintenant · {0} disponible",
    "Move money":
        "Déplacer de l'argent",
    "Move money between two of your accounts":
        "Déplacer de l'argent entre deux de vos comptes",
    "Move the money back to Available":
        "Remettre l'argent dans Disponible",
    "Move undone":
        "Mouvement annulé",
    "Moves money between your allocations and Available. Your accounts and your total balance do not change.":
        "Déplace de l'argent entre vos enveloppes et Disponible. Vos comptes et votre solde total ne changent pas.",
    "Moves money between your own accounts. Your total stays the same, and a transfer never counts as income or spending.":
        "Déplace de l'argent entre vos propres comptes. Votre total reste le même, et un virement ne compte jamais comme un revenu ou une dépense.",
    "Moves money from Available ({0}) into the allocation “{1}”. Your total balance does not change.":
        "Déplace de l'argent de Disponible ({0}) vers l'enveloppe « {1} ». Votre solde total ne change pas.",
    "Moves money from the allocation “{0}” ({1}) back to Available. Your total balance does not change.":
        "Déplace de l'argent de l'enveloppe « {0} » ({1}) vers Disponible. Votre solde total ne change pas.",
    "Moving money into an allocation never changes your total balance.":
        "Mettre de l'argent dans une enveloppe ne change jamais votre solde total.",
    "Must be text.":
        "Doit être du texte.",
    "Name":
        "Nom",
    "Name cannot be empty.":
        "Le nom ne peut pas être vide.",
    "Name cannot be longer than {0} characters.":
        "Le nom ne peut pas dépasser {0} caractères.",
    "Name must be text.":
        "Le nom doit être du texte.",
    "Near limit":
        "Proche de la limite",
    "Needed per month":
        "Nécessaire par mois",
    "negative balance adjustment":
        "ajustement négatif du solde",
    "Net":
        "Net",
    "Net change":
        "Variation nette",
    "Net invested":
        "Net investi",
    "Net worth":
        "Patrimoine net",
    "Never sent:\n":
        "Jamais envoyé :\n",
    "New":
        "Nouvelle",
    "New account":
        "Nouveau compte",
    "New account (Ctrl+N)":
        "Nouveau compte (Ctrl+N)",
    "New allocation":
        "Nouvelle enveloppe",
    "New allocation (Ctrl+N)":
        "Nouvelle enveloppe (Ctrl+N)",
    "New budget":
        "Nouveau budget",
    "New budget (Ctrl+N)":
        "Nouveau budget (Ctrl+N)",
    "New entry":
        "Nouvelle opération",
    "New expense category":
        "Nouvelle catégorie de dépenses",
    "New goal":
        "Nouvel objectif",
    "New goal (Ctrl+N)":
        "Nouvel objectif (Ctrl+N)",
    "New investment":
        "Nouvel investissement",
    "New investment (Ctrl+N)":
        "Nouvel investissement (Ctrl+N)",
    "New investment category":
        "Nouvelle catégorie d'investissement",
    "New loan":
        "Nouveau prêt",
    "New loan…":
        "Nouveau prêt…",
    "New name:":
        "Nouveau nom :",
    "New recurring entry":
        "Nouvelle opération récurrente",
    "New subscription":
        "Nouvel abonnement",
    "New subscription (Ctrl+N)":
        "Nouvel abonnement (Ctrl+N)",
    "New {0} category":
        "Nouvelle catégorie de {0}",
    "New…":
        "Nouvelle…",
    "Next date":
        "Prochaine date",
    "Next expected":
        "Prochain attendu",
    "Next payment":
        "Prochain paiement",
    "Next ›":
        "Suivant ›",
    "No accounts yet":
        "Aucun compte pour l'instant",
    "No active subscriptions":
        "Aucun abonnement actif",
    "No allocations yet — all of your money is Available.":
        "Aucune enveloppe pour l'instant — tout votre argent est Disponible.",
    "No Anthropic API key. Add one in Settings or set {0}.":
        "Aucune clé API Anthropic. Ajoutez-en une dans les Paramètres ou définissez {0}.",
    "No API key yet. Keys are kept in {0}, never in the database.":
        "Pas encore de clé API. Les clés sont gardées dans {0}, jamais dans la base de données.",
    "No balance exists before the account's opening date ({0}).":
        "Aucun solde n'existe avant la date d'ouverture du compte ({0}).",
    "No budgets yet":
        "Aucun budget pour l'instant",
    "No category yet — add one first":
        "Pas encore de catégorie — ajoutez-en une d'abord",
    "No comparison: the comparison period ({0}) starts before tracking began on {1}.":
        "Pas de comparaison : la période de comparaison ({0}) commence avant le début du suivi le {1}.",
    "No comparison: {0} – {1} is before tracking began":
        "Pas de comparaison : {0} – {1} est antérieur au début du suivi",
    "No contributions yet.":
        "Aucun versement pour l'instant.",
    "No deadline":
        "Sans échéance",
    "No expense categories yet — click New…":
        "Pas encore de catégorie de dépenses — cliquez sur Nouvelle…",
    "No expense categories yet.":
        "Aucune catégorie de dépenses pour l'instant.",
    "No expenses recorded this month":
        "Aucune dépense enregistrée ce mois-ci",
    "No free allocations":
        "Aucune enveloppe libre",
    "No goals yet":
        "Aucun objectif pour l'instant",
    "No goals yet. Create one to set money aside for something that matters.":
        "Aucun objectif pour l'instant. Créez-en un pour mettre de l'argent de côté pour ce qui compte.",
    "No income in this period":
        "Aucun revenu sur cette période",
    "No income or expenses recorded in the last months":
        "Aucun revenu ni dépense enregistré ces derniers mois",
    "No income recorded yet this month":
        "Aucun revenu enregistré ce mois-ci",
    "No income recorded, so there is no savings rate.":
        "Aucun revenu enregistré, donc pas de taux d'épargne.",
    "No income was recorded while spending was {0}.":
        "Aucun revenu n'a été enregistré alors que les dépenses s'élevaient à {0}.",
    "No investment categories — click New…":
        "Aucune catégorie d'investissement — cliquez sur Nouvelle…",
    "No investments yet":
        "Aucun investissement pour l'instant",
    "No loans or debts recorded.":
        "Aucun prêt ni dette enregistré.",
    "no local model (none chosen)":
        "aucun modèle local (aucun choisi)",
    "No matching transactions":
        "Aucune opération correspondante",
    "No payments due in the next 30 days.":
        "Aucun paiement prévu dans les 30 prochains jours.",
    "No published version was found.":
        "Aucune version publiée n'a été trouvée.",
    "No receipts yet.":
        "Aucun reçu pour l'instant.",
    "No recurring entries yet. Add your salary or rent to have them recorded for you.":
        "Aucune opération récurrente pour l'instant. Ajoutez votre salaire ou votre loyer pour qu'ils soient enregistrés pour vous.",
    "No regular weekly or monthly expenses detected in the last 12 months.":
        "Aucune dépense hebdomadaire ou mensuelle régulière détectée sur les 12 derniers mois.",
    "No return percentage: nothing is currently invested (withdrawals ≥ contributions).":
        "Pas de rendement en pourcentage : rien n'est investi actuellement (retraits ≥ versements).",
    "No rules yet.":
        "Aucune règle pour l'instant.",
    "No safety copies yet.":
        "Aucune copie de sécurité pour l'instant.",
    "No spending in this or the previous period":
        "Aucune dépense sur cette période ni sur la précédente",
    "No spending in this period":
        "Aucune dépense sur cette période",
    "No spending recorded.":
        "Aucune dépense enregistrée.",
    "No subscriptions yet":
        "Aucun abonnement pour l'instant",
    "No transactions yet":
        "Aucune opération pour l'instant",
    "No transactions yet.":
        "Aucune opération pour l'instant.",
    "No value entered yet.":
        "Aucune valeur saisie pour l'instant.",
    "No {0} categories yet — click New…":
        "Aucune catégorie de {0} pour l'instant — cliquez sur Nouvelle…",
    "None":
        "Aucun",
    "Not changed: Windows Hello did not answer.":
        "Inchangé : Windows Hello n'a pas répondu.",
    "Not changed: Windows Hello did not confirm it's you.":
        "Inchangé : Windows Hello n'a pas confirmé votre identité.",
    "Not found in your data, so possibly wrong: ":
        "Introuvable dans vos données, donc peut-être faux : ",
    "Not set aside for anything":
        "Mis de côté pour rien de précis",
    "Not through an account (only track it)":
        "Pas par un compte (simple suivi)",
    "Not valued yet":
        "Pas encore évalué",
    "Note":
        "Note",
    "Notes":
        "Notes",
    "Nothing due in this period.":
        "Rien à payer sur cette période.",
    "Nothing matches the current search and filters.":
        "Rien ne correspond à la recherche et aux filtres actuels.",
    "Nothing owed":
        "Rien à devoir",
    "Nothing set aside yet":
        "Rien de mis de côté pour l'instant",
    "Nothing set aside · as of {0}":
        "Rien de mis de côté · au {0}",
    "Nothing to compare with in the previous period":
        "Rien à comparer sur la période précédente",
    "Nov":
        "nov.",
    "Oct":
        "oct.",
    "Off":
        "Désactivée",
    "Offline · stored on this computer · version {0}":
        "Hors ligne · stocké sur cet ordinateur · version {0}",
    "Offline · stored on this PC":
        "Hors ligne · stocké sur ce PC",
    "Offset must be between zero and the number of records.":
        "Le décalage doit être compris entre zéro et le nombre d'enregistrements.",
    "Ollama address":
        "Adresse d'Ollama",
    "Ollama did not answer within {0} seconds.":
        "Ollama n'a pas répondu dans les {0} secondes.",
    "Ollama is not running at {0}. Start Ollama and try again.":
        "Ollama ne fonctionne pas sur {0}. Démarrez Ollama et réessayez.",
    "Ollama returned an empty answer.":
        "Ollama a renvoyé une réponse vide.",
    "Ollama returned an error (HTTP {0}){1}.":
        "Ollama a renvoyé une erreur (HTTP {0}){1}.",
    "Ollama returned an error: {0}":
        "Ollama a renvoyé une erreur : {0}",
    "Ollama sent an unreadable answer.":
        "Ollama a envoyé une réponse illisible.",
    "Ollama sent an unreadable model list.":
        "Ollama a envoyé une liste de modèles illisible.",
    "Ollama stopped before finishing the answer.":
        "Ollama s'est arrêté avant de terminer la réponse.",
    "on this computer":
        "sur cet ordinateur",
    "On track":
        "Dans les clous",
    "Once you start recording transactions, this page will summarise your balance, how your money is allocated and how this month compares to the last.":
        "Dès que vous enregistrez des opérations, cette page résume votre solde, la répartition de votre argent et la comparaison de ce mois-ci avec le précédent.",
    "One column (minus = money out)":
        "Une colonne (moins = sortie)",
    "Online (Anthropic Claude)":
        "En ligne (Anthropic Claude)",
    "Online AI (Anthropic) sends selected financial information — totals, rates, category spending and trends, never transaction descriptions or account names — to api.anthropic.com. You see exactly what would be sent and must confirm every request.":
        "L'IA en ligne (Anthropic) envoie certaines informations financières — totaux, taux, dépenses par catégorie et tendances, jamais les descriptions des opérations ni les noms des comptes — à api.anthropic.com. Vous voyez exactement ce qui serait envoyé et devez confirmer chaque demande.",
    "Online AI ({0}, Anthropic): each request sends a summary of your finances to {1}. You will see exactly what is sent and nothing leaves this computer until you confirm.{2}":
        "IA en ligne ({0}, Anthropic) : chaque demande envoie un résumé de vos finances à {1}. Vous verrez exactement ce qui est envoyé, et rien ne quitte cet ordinateur sans votre confirmation.{2}",
    "Online AI sends a summary of your finances to Anthropic ({0}). Before every request you will see exactly what would be sent, and nothing is sent unless you confirm.":
        "L'IA en ligne envoie un résumé de vos finances à Anthropic ({0}). Avant chaque demande, vous verrez exactement ce qui serait envoyé, et rien n'est envoyé sans votre confirmation.",
    "Only expense categories can be investment categories.":
        "Seules les catégories de dépenses peuvent être des catégories d'investissement.",
    "Only when I lock it":
        "Seulement quand je verrouille",
    "Only {0} is left to repay.":
        "Il ne reste que {0} à rembourser.",
    "Open":
        "En cours",
    "Open data folder":
        "Ouvrir le dossier des données",
    "Open the AI Advisor":
        "Ouvrir le conseiller IA",
    "Open without the lock":
        "Ouvrir sans le verrou",
    "Opening your data":
        "Ouverture de vos données",
    "Optional":
        "Facultatif",
    "Optional — broker, wallet, where the gold is kept …":
        "Facultatif — courtier, portefeuille, où l'or est gardé …",
    "Optional, e.g. Cash for the market":
        "Facultatif, ex. Espèces pour le marché",
    "Other":
        "Autres",
    "Over":
        "Dépassé",
    "Over budget":
        "Budget dépassé",
    "Over the limit":
        "Au-dessus de la limite",
    "Over-allocated by {0}: allocations exceed your real balance. Move money from an allocation back to Available.":
        "Enveloppes en excès de {0} : elles dépassent votre solde réel. Remettez de l'argent d'une enveloppe dans Disponible.",
    "Overdue":
        "En retard",
    "Overdue by {0} day{1}":
        "En retard de {0} jour{1}",
    "Overdue by {0} {1}":
        "En retard de {0} {1}",
    "Overspent":
        "Dépassement",
    "Overspent this month":
        "Dépenses supérieures aux revenus ce mois-ci",
    "Owed":
        "Dû",
    "Owed to you: {0} · You owe: {1} · In your net worth: {2}":
        "On vous doit : {0} · Vous devez : {1} · Dans votre patrimoine net : {2}",
    "Page size must be between 1 and {0}.":
        "La taille de page doit être comprise entre 1 et {0}.",
    "Paid from":
        "Payé depuis",
    "Paid from one of my accounts (records an investment expense)":
        "Payé depuis l'un de mes comptes (enregistre une dépense d'investissement)",
    "Paid from your accounts":
        "Payé depuis vos comptes",
    "Paid on":
        "Payé le",
    "Password for the backup":
        "Mot de passe de la sauvegarde",
    "Paste an Anthropic API key":
        "Collez une clé API Anthropic",
    "Pause":
        "Mettre en pause",
    "Paused":
        "En pause",
    "Per month":
        "Par mois",
    "Period":
        "Période",
    "Personal finance, kept local":
        "Finances personnelles, en local",
    "Personalised insights based on your own numbers.":
        "Des analyses personnalisées à partir de vos propres chiffres.",
    "Photos (JPG, PNG…) or PDFs up to {0} MB. They are kept with your data, included in backups, and deleted with the entry.":
        "Photos (JPG, PNG…) ou PDF jusqu'à {0} Mo. Ils sont gardés avec vos données, inclus dans les sauvegardes, et supprimés avec l'opération.",
    "Planned this month":
        "Prévu ce mois-ci",
    "Portfolio value":
        "Valeur du portefeuille",
    "positive balance adjustment":
        "ajustement positif du solde",
    "Pound sterling":
        "Livre sterling",
    "Preferences and where your data is stored.":
        "Préférences et emplacement de vos données.",
    "Previous":
        "Précédente",
    "Previous period":
        "Période précédente",
    "Previous period is before tracking began":
        "La période précédente est antérieure au début du suivi",
    "Privacy":
        "Confidentialité",
    "processed on this computer":
        "traité sur cet ordinateur",
    "Profit / loss":
        "Gain / perte",
    "Progress":
        "Progression",
    "Protect the backup with a password (encrypted)":
        "Protéger la sauvegarde par un mot de passe (chiffrée)",
    "Protected backup":
        "Sauvegarde protégée",
    "Protected Money Manager backup":
        "Sauvegarde Money Manager protégée",
    "Provider":
        "Fournisseur",
    "Put into":
        "Mis dans",
    "Python":
        "Python",
    "Qt / PySide6":
        "Qt / PySide6",
    "Question":
        "Question",
    "Question for the advisor":
        "Question pour le conseiller",
    "Ready":
        "Prêt",
    "Ready: {0} on this computer.":
        "Prêt : {0} sur cet ordinateur.",
    "Recalculate the summary from your latest data.":
        "Recalculer le résumé à partir de vos données les plus récentes.",
    "Receipt {0!r} does not exist.":
        "Le reçu {0!r} n'existe pas.",
    "Receipts":
        "Reçus",
    "Receipts…":
        "Reçus…",
    "Received into":
        "Reçu sur",
    "Recent moves":
        "Mouvements récents",
    "Recent transactions":
        "Opérations récentes",
    "Record":
        "Enregistrer",
    "Record a transaction":
        "Enregistrer une opération",
    "Record contributions to your investments and see how they add up.":
        "Enregistrez vos versements sur vos investissements et voyez ce qu'ils représentent.",
    "Record how much you have saved for this goal outside the app. This amount is not part of your balance.":
        "Indiquez combien vous avez épargné pour cet objectif en dehors de l'application. Ce montant ne fait pas partie de votre solde.",
    "Record payment":
        "Enregistrer le paiement",
    "Record payment · {0}":
        "Enregistrer le paiement · {0}",
    "Record repayment…":
        "Enregistrer un remboursement…",
    "Record withdrawal":
        "Enregistrer un retrait",
    "Record your first income or expense. Your balance updates automatically.":
        "Enregistrez votre premier revenu ou votre première dépense. Votre solde se met à jour automatiquement.",
    "Recorded automatically (recurring)":
        "Enregistré automatiquement (récurrent)",
    "Recorded automatically on each date — when Money Manager is open, or the next time it starts. A first date in the past records the dates since then (up to a year).":
        "Enregistrée automatiquement à chaque date — quand Money Manager est ouvert, ou au prochain démarrage. Une première date dans le passé enregistre les dates depuis (jusqu'à un an).",
    "Recorded now: {0}.":
        "Enregistré maintenant : {0}.",
    "Recording income and expenses with your own categories is coming in the next sprint.":
        "L'enregistrement des revenus et des dépenses avec vos propres catégories arrive bientôt.",
    "Records one expense in the investment category, so your balance goes down and the statistics count it as investing.":
        "Enregistre une dépense dans la catégorie d'investissement : votre solde baisse et les statistiques la comptent comme un investissement.",
    "Recurring entries":
        "Opérations récurrentes",
    "Recurring entry {0!r} does not exist.":
        "L'opération récurrente {0!r} n'existe pas.",
    "recurring expense":
        "dépense récurrente",
    "recurring expenses":
        "dépenses récurrentes",
    "Recurring spending":
        "Dépenses récurrentes",
    "Recurring…":
        "Récurrentes…",
    "Refresh":
        "Actualiser",
    "Regenerate":
        "Régénérer",
    "Released when archived":
        "Libéré à l'archivage",
    "Remove":
        "Supprimer",
    "Remove budget":
        "Supprimer le budget",
    "Remove key":
        "Supprimer la clé",
    "Remove receipt":
        "Retirer le reçu",
    "Remove the budget for {0}?\n\nYour spending and the category itself are not affected.":
        "Supprimer le budget de {0} ?\n\nVos dépenses et la catégorie elle-même ne sont pas touchées.",
    "Remove the repayment of {0} on {1}? If it moved money through an account, that adjustment is removed too.":
        "Retirer le remboursement de {0} du {1} ? S'il est passé par un compte, cet ajustement est retiré aussi.",
    "Remove {0}?":
        "Retirer {0} ?",
    "Rename":
        "Renommer",
    "Rename allocation":
        "Renommer l'enveloppe",
    "Renewing soon":
        "Renouvellements à venir",
    "Repaid":
        "Remboursé",
    "Repay by":
        "Remboursement avant",
    "Repayment from {0}":
        "Remboursement de {0}",
    "Repayment recorded":
        "Remboursement enregistré",
    "Repayment removed":
        "Remboursement retiré",
    "Repayment to {0}":
        "Remboursement à {0}",
    "Repayment {0!r} does not exist.":
        "Le remboursement {0!r} n'existe pas.",
    "Repeats":
        "Répétition",
    "Replace ALL current data with this backup from {0}?\n\nThe backup has {1} accounts, {2} transactions, {3} goals and {4} records in total (currency: {5}).\n\nYour current data is first saved to a safety backup next to the database.":
        "Remplacer TOUTES les données actuelles par cette sauvegarde du {0} ?\n\nLa sauvegarde contient {1} comptes, {2} opérations, {3} objectifs et {4} enregistrements au total (devise : {5}).\n\nVos données actuelles sont d'abord enregistrées dans une sauvegarde de sécurité à côté de la base de données.",
    "Replace ALL current data with this safety copy?\n\n{0}\n\nYour current data is first saved as a new safety copy, so you can come back to it.":
        "Remplacer TOUTES les données actuelles par cette copie de sécurité ?\n\n{0}\n\nVos données actuelles sont d'abord enregistrées comme nouvelle copie de sécurité, pour pouvoir y revenir.",
    "Replace my data":
        "Remplacer mes données",
    "Report saved":
        "Rapport enregistré",
    "Reset all data":
        "Réinitialiser toutes les données",
    "Reset all data…":
        "Réinitialiser toutes les données…",
    "Reset application data":
        "Réinitialiser les données de l'application",
    "Reset complete":
        "Réinitialisation terminée",
    "Restart now":
        "Redémarrer maintenant",
    "Restore":
        "Restaurer",
    "Restore complete":
        "Restauration terminée",
    "Restore safety copy":
        "Restaurer une copie de sécurité",
    "restored":
        "restauré",
    "Restore…":
        "Restaurer…",
    "Resume":
        "Reprendre",
    "Return":
        "Rendement",
    "Return calculated from your latest value.":
        "Rendement calculé d'après votre dernière valeur.",
    "Return this money to where it came from":
        "Renvoyer cet argent d'où il vient",
    "Returns its money to Available":
        "Renvoie son argent dans Disponible",
    "rising":
        "en hausse",
    "Rule {0!r} does not exist.":
        "La règle {0!r} n'existe pas.",
    "Runs on this computer with Ollama. Nothing is sent over the internet.":
        "Fonctionne sur cet ordinateur avec Ollama. Rien n'est envoyé sur Internet.",
    "Safety copies":
        "Copies de sécurité",
    "safety copy":
        "copie de sécurité",
    "Same as Windows":
        "Comme Windows",
    "Saturdays":
        "le samedi",
    "Saudi riyal":
        "Riyal saoudien",
    "Save":
        "Enregistrer",
    "Save a copy automatically each day (the last 30 are kept)":
        "Enregistrer une copie automatiquement chaque jour (les 30 dernières sont gardées)",
    "Save a month's summary as a PDF you can print or keep":
        "Enregistrer le résumé d'un mois en PDF, à imprimer ou à garder",
    "Save a summary of a whole year as a PDF":
        "Enregistrer le résumé d'une année entière en PDF",
    "Save AI settings":
        "Enregistrer les paramètres de l'IA",
    "Save budget":
        "Enregistrer le budget",
    "Save changes":
        "Enregistrer",
    "Save key":
        "Enregistrer la clé",
    "Save the monthly report":
        "Enregistrer le rapport mensuel",
    "Save value":
        "Enregistrer la valeur",
    "Save {0} per month to finish on time.":
        "Épargnez {0} par mois pour finir à temps.",
    "Saved":
        "Épargné",
    "Saved so far":
        "Épargné jusqu'ici",
    "Saved this month":
        "Épargné ce mois-ci",
    "Saved towards goals":
        "Épargné pour les objectifs",
    "Savings rate":
        "Taux d'épargne",
    "Savings rate {0}":
        "Taux d'épargne {0}",
    "Savings were {0}, {1} of income.":
        "L'épargne s'élève à {0}, soit {1} des revenus.",
    "Search description, notes, category or amount":
        "Rechercher dans la description, les notes, la catégorie ou le montant",
    "Search entries":
        "Rechercher des opérations",
    "Search text cannot be longer than {0} characters.":
        "Le texte recherché ne peut pas dépasser {0} caractères.",
    "Search transactions":
        "Rechercher des opérations",
    "Search transactions: type and press Enter":
        "Rechercher des opérations : tapez puis appuyez sur Entrée",
    "See whether your spending and saving are improving.":
        "Voyez si vos dépenses et votre épargne s'améliorent.",
    "selected period":
        "période choisie",
    "Send financial information to {0}?":
        "Envoyer des informations financières à {0} ?",
    "Send to {0}":
        "Envoyer à {0}",
    "Sending financial information to {0} needs your confirmation first.":
        "L'envoi d'informations financières à {0} nécessite d'abord votre confirmation.",
    "sent to Anthropic":
        "envoyé à Anthropic",
    "Sep":
        "sept.",
    "Separate debit and credit columns":
        "Colonnes débit et crédit séparées",
    "Set a deadline":
        "Fixer une échéance",
    "Set a deadline to see how much to save each month.":
        "Fixez une échéance pour voir combien épargner chaque mois.",
    "Set a monthly limit for a spending category, such as groceries or eating out, and see at a glance how much is left this month.":
        "Fixez une limite mensuelle pour une catégorie de dépenses, comme les courses ou les restaurants, et voyez d'un coup d'œil ce qu'il reste ce mois-ci.",
    "Set a monthly limit for a spending category.":
        "Fixez une limite mensuelle pour une catégorie de dépenses.",
    "Set aside":
        "Mis de côté",
    "set aside":
        "mis de côté",
    "Set aside now (from Available)":
        "Mettre de côté maintenant (depuis Disponible)",
    "Set financial targets and track your progress.":
        "Fixez des objectifs financiers et suivez votre progression.",
    "Set money aside for purposes; what is left is Available to spend.":
        "Mettez de l'argent de côté pour des usages précis ; le reste est Disponible.",
    "Settings":
        "Paramètres",
    "Settings → Updates → Download":
        "Paramètres → Mises à jour → Télécharger",
    "Share":
        "Part",
    "Share of this month's income you kept":
        "Part des revenus du mois que vous avez gardée",
    "Share of your balance set aside in allocations":
        "Part de votre solde mise de côté dans des enveloppes",
    "Show archived":
        "Afficher les archivés",
    "Show the values as a table":
        "Afficher les valeurs dans un tableau",
    "Show {0} as a table":
        "Afficher {0} dans un tableau",
    "Showing {0}–{1} of {2}":
        "{0}–{1} sur {2}",
    "Simple indicators based on your own data":
        "Indicateurs simples tirés de vos propres données",
    "Since the start: in {0} · out {1}":
        "Depuis le début : entrées {0} · sorties {1}",
    "Skip":
        "Passer",
    "Skip payment":
        "Passer le paiement",
    "Skip the payment of “{0}” due {1}? No expense is recorded — use this if you already entered it or it was not charged.":
        "Passer le paiement de « {0} » dû le {1} ? Aucune dépense n'est enregistrée — utilisez ceci si vous l'avez déjà saisi ou s'il n'a pas été prélevé.",
    "Some lines were not imported":
        "Certaines lignes n'ont pas été importées",
    "Something went wrong":
        "Un problème est survenu",
    "Source":
        "Origine",
    "Spending":
        "Dépenses",
    "Spending analysis":
        "Analyse des dépenses",
    "Spending by category":
        "Dépenses par catégorie",
    "Spending change compares with the previous month (the current month with the same days of last month).":
        "La variation des dépenses se compare au mois précédent (le mois en cours avec les mêmes jours du mois dernier).",
    "Spending goes to":
        "Les dépenses vont dans",
    "Spending per category, this period vs the previous one · {0}":
        "Dépenses par catégorie, cette période contre la précédente · {0}",
    "Spending trend":
        "Tendance des dépenses",
    "Spending vs last month":
        "Dépenses par rapport au mois dernier",
    "Spending vs prev.":
        "Dépenses vs préc.",
    "Spending was {0} of income.":
        "Les dépenses représentent {0} des revenus.",
    "Spent":
        "Dépensé",
    "Spent so far":
        "Dépensé jusqu'ici",
    "SQLite":
        "SQLite",
    "Start date":
        "Date de début",
    "start must not be after end":
        "le début ne doit pas être après la fin",
    "Statement imported":
        "Relevé importé",
    "Statistics":
        "Statistiques",
    "Statistics are calculated from your recorded transactions. Add the account you want to track first.":
        "Les statistiques sont calculées à partir de vos opérations. Ajoutez d'abord le compte que vous voulez suivre.",
    "statistics page":
        "la page Statistiques",
    "Status":
        "Statut",
    "Stock":
        "Action",
    "Stop recording “{0}”? Entries already recorded are kept.":
        "Arrêter d'enregistrer « {0} » ? Les opérations déjà enregistrées sont conservées.",
    "Stored API key removed.":
        "Clé API enregistrée supprimée.",
    "Stored only in your local database.":
        "Enregistré uniquement dans votre base de données locale.",
    "Subscription payment due {0}":
        "Paiement d'abonnement dû le {0}",
    "Subscription {0!r} does not exist.":
        "L'abonnement {0!r} n'existe pas.",
    "Subscriptions":
        "Abonnements",
    "Subscriptions & Bills":
        "Abonnements et factures",
    "Suggestions":
        "Suggestions",
    "Summary":
        "Résumé",
    "Sundays":
        "le dimanche",
    "Swiss franc":
        "Franc suisse",
    "Table":
        "Tableau",
    "Take out":
        "Retirer",
    "Target":
        "Objectif",
    "Target ({0})":
        "Objectif ({0})",
    "Target reached":
        "Objectif atteint",
    "Test connection":
        "Tester la connexion",
    "The account '{0}' has transactions and cannot be deleted.":
        "Le compte « {0} » contient des opérations et ne peut pas être supprimé.",
    "The account to transfer from does not exist.":
        "Le compte de départ n'existe pas.",
    "The account to transfer to does not exist.":
        "Le compte de destination n'existe pas.",
    "The advisor explains figures calculated from your recorded transactions. Add the account you want to track first.":
        "Le conseiller explique des chiffres calculés à partir de vos opérations. Ajoutez d'abord le compte que vous voulez suivre.",
    "The AI request failed unexpectedly.":
        "La demande à l'IA a échoué de façon inattendue.",
    "The allocation '{0}' already holds the money for the goal '{1}'. Money can count towards only one goal.":
        "L'enveloppe « {0} » contient déjà l'argent de l'objectif « {1} ». L'argent ne peut compter que pour un seul objectif.",
    "The allocation '{0}' has a negative balance; run a consistency check.":
        "L'enveloppe « {0} » a un solde négatif ; lancez une vérification de cohérence.",
    "The allocation '{0}' has transfers or transactions; archive it instead.":
        "L'enveloppe « {0} » a des mouvements ou des opérations ; archivez-la plutôt.",
    "The allocation '{0}' holds the money for the goal '{1}'; delete the goal first.":
        "L'enveloppe « {0} » contient l'argent de l'objectif « {1} » ; supprimez d'abord l'objectif.",
    "The allocation '{0}' holds {1}; this change would leave it at {2}. Move money into it first, or record the transaction against Available.":
        "L'enveloppe « {0} » contient {1} ; cette modification la laisserait à {2}. Ajoutez-y d'abord de l'argent, ou enregistrez l'opération sur Disponible.",
    "The allocation '{0}' is archived, and this change would put money back into it. Restore the allocation first, or record the transaction against Available.":
        "L'enveloppe « {0} » est archivée, et cette modification y remettrait de l'argent. Restaurez d'abord l'enveloppe, ou enregistrez l'opération sur Disponible.",
    "The allocation '{0}' is archived.":
        "L'enveloppe « {0} » est archivée.",
    "The allocation '{0}' is archived; restore it before undoing.":
        "L'enveloppe « {0} » est archivée ; restaurez-la avant d'annuler.",
    "The allocation '{0}' is negative ({1}).":
        "L'enveloppe « {0} » est négative ({1}).",
    "The amount and the date stay as recorded; repayments lower what is left.":
        "Le montant et la date restent tels qu'enregistrés ; les remboursements diminuent ce qui reste.",
    "The amount cannot be negative.":
        "Le montant ne peut pas être négatif.",
    "The answer could not be saved: {0}":
        "La réponse n'a pas pu être enregistrée : {0}",
    "The archived allocation '{0}' still holds {1}.":
        "L'enveloppe archivée « {0} » contient encore {1}.",
    "The backup could not be verified after writing it.":
        "La sauvegarde n'a pas pu être vérifiée après son écriture.",
    "the backup format version is not supported.":
        "la version du format de sauvegarde n'est pas prise en charge.",
    "The backup from {0} was imported.":
        "La sauvegarde du {0} a été importée.",
    "The balance changed by {0}{1} from {2}.":
        "Le solde a varié de {0}{1} depuis le {2}.",
    "The balance history appears after your first days of tracking":
        "L'historique du solde apparaît après vos premiers jours de suivi",
    "The category '{0}' is archived.":
        "La catégorie « {0} » est archivée.",
    "The category '{0}' is used by a subscription; change the subscription's category first.":
        "La catégorie « {0} » est utilisée par un abonnement ; changez d'abord la catégorie de l'abonnement.",
    "The category '{0}' is used by transactions; archive it instead.":
        "La catégorie « {0} » est utilisée par des opérations ; archivez-la plutôt.",
    "The check failed.":
        "La vérification a échoué.",
    "The configuration file named by {0} does not exist: {1}":
        "Le fichier de configuration indiqué par {0} n'existe pas : {1}",
    "The currency can only be changed before any account exists, because Money Manager never converts amounts between currencies.":
        "La devise ne peut être changée qu'avant la création du premier compte, car Money Manager ne convertit jamais les montants d'une devise à l'autre.",
    "The dashboard summarises your real balance, income, spending and allocations. Add the account you want to track first.":
        "Le tableau de bord résume votre solde réel, vos revenus, vos dépenses et vos enveloppes. Ajoutez d'abord le compte que vous voulez suivre.",
    "The data you had before was saved to:\n{0}":
        "Les données que vous aviez avant ont été enregistrées dans :\n{0}",
    "The deadline cannot be in the past.":
        "L'échéance ne peut pas être dans le passé.",
    "The deadline has passed. Edit the goal to set a new one.":
        "L'échéance est passée. Modifiez l'objectif pour en fixer une nouvelle.",
    "The deadline must be within {0} years.":
        "L'échéance doit être dans les {0} ans.",
    "The due date cannot be before the start date.":
        "L'échéance ne peut pas précéder la date de début.",
    "The file has no lines to import.":
        "Le fichier ne contient aucune ligne à importer.",
    "the file is damaged or was edited (checksum mismatch).":
        "le fichier est endommagé ou a été modifié (somme de contrôle différente).",
    "The file is empty.":
        "Le fichier est vide.",
    "The file is larger than {0} MB.":
        "Le fichier dépasse {0} Mo.",
    "the file is not readable JSON.":
        "le fichier n'est pas un JSON lisible.",
    "The file is too large for a bank statement.":
        "Le fichier est trop volumineux pour un relevé bancaire.",
    "the file is too large.":
        "le fichier est trop volumineux.",
    "the file was not exported by Money Manager.":
        "le fichier n'a pas été exporté par Money Manager.",
    "The file's contents do not match its type.":
        "Le contenu du fichier ne correspond pas à son type.",
    "The file's text encoding is not supported.":
        "L'encodage du texte de ce fichier n'est pas pris en charge.",
    "The first date cannot be before the account was opened ({0}).":
        "La première date ne peut pas précéder l'ouverture du compte ({0}).",
    "The first date cannot be more than a year ago.":
        "La première date ne peut pas remonter à plus d'un an.",
    "The first date must be within {0} years.":
        "La première date doit être dans les {0} ans.",
    "The information to send changed after you agreed. Review it and confirm again.":
        "Les informations à envoyer ont changé après votre accord. Vérifiez-les et confirmez à nouveau.",
    "The initial amount cannot be negative.":
        "Le montant initial ne peut pas être négatif.",
    "The line has no amount.":
        "La ligne n'a pas de montant.",
    "The line has too few columns.":
        "La ligne a trop peu de colonnes.",
    "the local model ({0}) when Ollama is running":
        "le modèle local ({0}) quand Ollama fonctionne",
    "The lock is off.":
        "Le verrou est désactivé.",
    "The lock is on.":
        "Le verrou est activé.",
    "The model '{0}' is not installed in Ollama. Run 'ollama pull {1}' first.":
        "Le modèle « {0} » n'est pas installé dans Ollama. Exécutez d'abord « ollama pull {1} ».",
    "The model '{0}' is not installed. Run 'ollama pull {1}'.":
        "Le modèle « {0} » n'est pas installé. Exécutez « ollama pull {1} ».",
    "The model '{0}' was not found at Anthropic.":
        "Le modèle « {0} » est introuvable chez Anthropic.",
    "The model name is not valid.":
        "Le nom du modèle n'est pas valide.",
    "The next payment date cannot be more than a year in the past.":
        "La prochaine date de paiement ne peut pas remonter à plus d'un an.",
    "The next payment date must be within {0} years.":
        "La prochaine date de paiement doit être dans les {0} ans.",
    "The next payment of '{0}' to confirm is the one due {1}.":
        "Le prochain paiement de « {0} » à confirmer est celui dû le {1}.",
    "The online provider needs the optional 'anthropic' package. Install it with pip install \"money-manager[ai-online]\".":
        "Le fournisseur en ligne nécessite le paquet optionnel « anthropic ». Installez-le avec pip install \"money-manager[ai-online]\".",
    "The opening date cannot be after the account's first transaction ({0}).":
        "La date d'ouverture ne peut pas être après la première opération du compte ({0}).",
    "The password is wrong, or the file is damaged.":
        "Le mot de passe est incorrect, ou le fichier est endommagé.",
    "The payment of '{0}' due {1} has already been confirmed.":
        "Le paiement de « {0} » dû le {1} a déjà été confirmé.",
    "The period cannot end in the future.":
        "La période ne peut pas se terminer dans le futur.",
    "The period cannot start before {0}.":
        "La période ne peut pas commencer avant le {0}.",
    "The port number is not valid.":
        "Le numéro de port n'est pas valide.",
    "The provider declined to answer this request.":
        "Le fournisseur a refusé de répondre à cette demande.",
    "The provider returned an empty answer.":
        "Le fournisseur a renvoyé une réponse vide.",
    "The range cannot end in the future.":
        "La période ne peut pas se terminer dans le futur.",
    "The range cannot start before {0}.":
        "La période ne peut pas commencer avant le {0}.",
    "The report could not be written to {0}.":
        "Le rapport n'a pas pu être écrit dans {0}.",
    "The saved API key was removed.":
        "La clé API enregistrée a été supprimée.",
    "The selected account does not exist.":
        "Le compte choisi n'existe pas.",
    "The selected allocation does not exist.":
        "L'enveloppe choisie n'existe pas.",
    "The selected category does not exist.":
        "La catégorie choisie n'existe pas.",
    "The source and destination must be different.":
        "La source et la destination doivent être différentes.",
    "The start date must not be after the end date.":
        "La date de début ne doit pas être après la date de fin.",
    "The summary below is processed by {0} running on this computer. Nothing is sent over the internet.":
        "Le résumé ci-dessous est traité par {0} sur cet ordinateur. Rien n'est envoyé sur Internet.",
    "the table '{0}' does not have the expected columns.":
        "la table « {0} » n'a pas les colonnes attendues.",
    "The timeout must be between {0} and {1} seconds.":
        "Le délai doit être compris entre {0} et {1} secondes.",
    "The two passwords are different. Nothing was exported.":
        "Les deux mots de passe sont différents. Rien n'a été exporté.",
    "The update server answered with an error ({0}).":
        "Le serveur de mises à jour a répondu par une erreur ({0}).",
    "The update server sent an unexpected answer.":
        "Le serveur de mises à jour a envoyé une réponse inattendue.",
    "The whole year":
        "L'année entière",
    "The Windows Credential Manager is only available on Windows.":
        "Le Gestionnaire d'identification Windows n'existe que sous Windows.",
    "The {0} could not be {1}; your data was not changed.":
        "L'opération a échoué ({0}) : rien n'a été {1} ; vos données n'ont pas été modifiées.",
    "The {0}'s records do not fit together (broken references). Nothing was {1}.":
        "Les enregistrements ({0}) ne concordent pas (références cassées). Rien n'a été {1}.",
    "Theme":
        "Thème",
    "There is no financial data to analyse yet. Create an account and record some transactions first.":
        "Il n'y a pas encore de données financières à analyser. Créez un compte et enregistrez d'abord quelques opérations.",
    "This allocation holds a goal's money; manage it on the Goals page":
        "Cette enveloppe contient l'argent d'un objectif ; gérez-la depuis la page Objectifs",
    "This analysis and task were given to the AI ":
        "Cette analyse et cette tâche ont été données à l'IA ",
    "This API key is not allowed to use the model.":
        "Cette clé API n'est pas autorisée à utiliser ce modèle.",
    "This backup is protected by a password.":
        "Cette sauvegarde est protégée par un mot de passe.",
    "This backup is protected. Password:":
        "Cette sauvegarde est protégée. Mot de passe :",
    "This backup was made with a newer version of Money Manager (data schema {0}). Update Money Manager to import it.":
        "Cette sauvegarde a été faite avec une version plus récente de Money Manager (schéma de données {0}). Mettez Money Manager à jour pour l'importer.",
    "This category has no budget.":
        "Cette catégorie n'a pas de budget.",
    "this computer":
        "cet ordinateur",
    "This deletes every account, transaction, allocation, goal, subscription, investment, setting and AI insight. A safety backup of the database is written next to it first. Export a backup yourself if you want to keep a copy elsewhere.":
        "Cela supprime tous les comptes, opérations, enveloppes, objectifs, abonnements, investissements, paramètres et analyses d'IA. Une sauvegarde de sécurité de la base de données est d'abord écrite à côté. Exportez vous-même une sauvegarde si vous voulez en garder une copie ailleurs.",
    "This does not look like an API key.":
        "Cela ne ressemble pas à une clé API.",
    "This entry":
        "Cette opération",
    "This entry is one side of a transfer between your accounts. Delete the transfer to remove both sides; to change it, delete it and record it again.":
        "Cette opération est l'un des deux côtés d'un virement entre vos comptes. Supprimez le virement pour retirer les deux côtés ; pour le modifier, supprimez-le puis enregistrez-le à nouveau.",
    "This entry is one side of a transfer between your accounts. To change it, delete the transfer and record it again.":
        "Cette opération est l'un des deux côtés d'un virement entre vos comptes. Pour la modifier, supprimez le virement et enregistrez-le à nouveau.",
    "This expense is an investment contribution and must stay an expense. Delete it on the Investments page instead.":
        "Cette dépense est un versement sur un investissement et doit rester une dépense. Supprimez-la plutôt depuis la page Investissements.",
    "This goal's progress is the balance of its allocation; add or withdraw money instead.":
        "La progression de cet objectif est le solde de son enveloppe ; ajoutez ou retirez plutôt de l'argent.",
    "This insight no longer exists.":
        "Cette analyse n'existe plus.",
    "This is not a valid Money Manager backup: {0}":
        "Ce n'est pas une sauvegarde Money Manager valide : {0}",
    "This is version {0}. Money Manager can ask GitHub once a day whether a newer version exists. Only that question is sent — nothing about you or your data (GitHub sees your IP address, as with any web request). Nothing is downloaded by itself.":
        "Ceci est la version {0}. Money Manager peut demander à GitHub une fois par jour si une version plus récente existe. Seule cette question est envoyée — rien sur vous ni sur vos données (GitHub voit votre adresse IP, comme pour toute requête web). Rien n'est téléchargé tout seul.",
    "This model runs on Ollama's servers, not on this computer. Choose a local model.":
        "Ce modèle fonctionne sur les serveurs d'Ollama, pas sur cet ordinateur. Choisissez un modèle local.",
    "This month":
        "Ce mois-ci",
    "This month · top 5, the rest grouped as Other":
        "Ce mois-ci · les 5 premières, le reste regroupé dans Autres",
    "This payment is not due until {0}; it can be confirmed at most {1} days early.":
        "Ce paiement n'est dû que le {0} ; il peut être confirmé au plus {1} jours à l'avance.",
    "This period":
        "Cette période",
    "This safety copy cannot be read.":
        "Cette copie de sécurité est illisible.",
    "This safety copy cannot be restored: {0}":
        "Cette copie de sécurité ne peut pas être restaurée : {0}",
    "This safety copy is damaged and cannot be restored.":
        "Cette copie de sécurité est endommagée et ne peut pas être restaurée.",
    "This year":
        "Cette année",
    "Thursdays":
        "le jeudi",
    "Tick the expense categories where money goes into investments (stocks, retirement funds, …). They count towards your investment rate and as saving rather than spending.":
        "Cochez les catégories de dépenses où l'argent part dans des investissements (actions, épargne retraite, …). Elles comptent dans votre taux d'investissement et comme épargne plutôt que comme dépense.",
    "Tiles rise into place, figures count up, bars and rings fill, and a short notice confirms each change. Switch off for a still interface.":
        "Les tuiles se mettent en place, les chiffres défilent, les barres et anneaux se remplissent, et une courte notification confirme chaque modification. Désactivez pour une interface immobile.",
    "Timeout":
        "Délai d'attente",
    "To":
        "Vers",
    "To date":
        "Au",
    "To keep the data somewhere else (for example a portable drive), set data_dir in MoneyManager.ini next to MoneyManager.exe, or start Money Manager with the environment variable MONEY_MANAGER_DATA_DIR set to that folder. The folder cannot be moved from inside the app, so that data is never lost halfway through a move; use Export backup and Import backup to copy data between folders.":
        "Pour garder les données ailleurs (par exemple sur un disque portable), indiquez data_dir dans MoneyManager.ini à côté de MoneyManager.exe, ou lancez Money Manager avec la variable d'environnement MONEY_MANAGER_DATA_DIR réglée sur ce dossier. Le dossier ne peut pas être déplacé depuis l'application, pour que les données ne soient jamais perdues en plein déplacement ; utilisez Exporter et Importer une sauvegarde pour copier les données d'un dossier à l'autre.",
    "To meet every deadline":
        "Pour tenir toutes les échéances",
    "To {0}":
        "Vers {0}",
    "Today":
        "Aujourd'hui",
    "Tomorrow":
        "Demain",
    "Total balance":
        "Solde total",
    "Total balance at the end of each day":
        "Solde total à la fin de chaque jour",
    "Total balance mismatch: {0} vs {1}.":
        "Écart sur le solde total : {0} contre {1}.",
    "Track stocks, ETFs, crypto, gold or anything else: record what you put in and, from time to time, what it is worth. Profit and return appear once a value is entered.":
        "Suivez actions, ETF, cryptomonnaies, or ou autre : enregistrez ce que vous y mettez et, de temps en temps, ce que cela vaut. Le gain et le rendement apparaissent dès qu'une valeur est saisie.",
    "Track subscriptions and bills, their billing cycles and upcoming due dates.":
        "Suivez vos abonnements et factures, leurs échéances et les prochains paiements.",
    "Tracked manually — not part of your balance":
        "Suivi à la main — ne fait pas partie de votre solde",
    "Tracked manually — not part of your balance.":
        "Suivi à la main — ne fait pas partie de votre solde.",
    "Tracked since {0} · opening balance {1}":
        "Suivi depuis le {0} · solde d'ouverture {1}",
    "Transaction {0!r} does not exist.":
        "L'opération {0!r} n'existe pas.",
    "Transactions":
        "Opérations",
    "Transactions are recorded against an account, such as your bank account or cash. Enter its current balance and start tracking from today.":
        "Les opérations sont enregistrées sur un compte, comme votre compte bancaire ou vos espèces. Saisissez son solde actuel et commencez le suivi dès aujourd'hui.",
    "Transactions → Recurring…":
        "Opérations → Récurrentes…",
    "Transfer":
        "Virement",
    "Transfer between accounts":
        "Virement entre comptes",
    "Transfer between your accounts: {0}":
        "Virement entre vos comptes : {0}",
    "Transfer deleted":
        "Virement supprimé",
    "Transfer from {0}":
        "Virement depuis {0}",
    "Transfer in":
        "Virement reçu",
    "Transfer out":
        "Virement émis",
    "Transfer recorded":
        "Virement enregistré",
    "Transfer to {0}":
        "Virement vers {0}",
    "Transfer {0!r} does not exist.":
        "Le virement {0!r} n'existe pas.",
    "Transfers cannot be edited":
        "Les virements ne peuvent pas être modifiés",
    "Transfers move money between them":
        "Les virements déplacent l'argent entre eux",
    "Tuesdays":
        "le mardi",
    "Turn off the Money Manager lock":
        "Désactiver le verrou de Money Manager",
    "Turn on the Money Manager lock":
        "Activer le verrou de Money Manager",
    "Type":
        "Type",
    "Type a question about your finances.":
        "Posez une question sur vos finances.",
    "Type the password again:":
        "Tapez à nouveau le mot de passe :",
    "Type {0} to confirm":
        "Tapez {0} pour confirmer",
    "Type {0} to confirm.":
        "Tapez {0} pour confirmer.",
    "Typical amount":
        "Montant habituel",
    "UAE dirham":
        "Dirham des Émirats",
    "Uncategorised":
        "Sans catégorie",
    "Undo":
        "Annuler",
    "Undo last repayment":
        "Annuler le dernier remboursement",
    "Undo move":
        "Annuler le mouvement",
    "Undo repayment":
        "Annuler le remboursement",
    "Undo this move?\n\n{0} · {1} · {2}":
        "Annuler ce mouvement ?\n\n{0} · {1} · {2}",
    "Unknown fill colour: {0!r}":
        "Couleur de remplissage inconnue : {0!r}",
    "Unknown page: {0!r}":
        "Page inconnue : {0!r}",
    "Unknown setting(s) {0} in '{1}'; expected {2}.":
        "Paramètre(s) inconnu(s) {0} dans « {1} » ; attendu : {2}.",
    "Unlock Money Manager":
        "Déverrouiller Money Manager",
    "Unlock was cancelled. Choose Unlock to try again.":
        "Déverrouillage annulé. Choisissez Déverrouiller pour réessayer.",
    "Unlock with Windows Hello":
        "Déverrouiller avec Windows Hello",
    "Unsupported amount type: {0}.":
        "Type de montant non pris en charge : {0}.",
    "Unsupported value type {0}":
        "Type de valeur non pris en charge : {0}",
    "Upcoming payments":
        "Paiements à venir",
    "Update amount":
        "Mettre à jour le montant",
    "Update the values of your investments to see returns":
        "Mettez à jour la valeur de vos investissements pour voir les rendements",
    "Update value":
        "Mettre à jour la valeur",
    "Update value · {0}":
        "Mettre à jour la valeur · {0}",
    "Update {0}":
        "Mettre à jour {0}",
    "Updates":
        "Mises à jour",
    "Updating…":
        "Mise à jour…",
    "US dollar":
        "Dollar américain",
    "Use a password of at least {0} characters.":
        "Utilisez un mot de passe d'au moins {0} caractères.",
    "Use either a comma or a dot for decimals, and spaces to group thousands.":
        "Utilisez soit une virgule soit un point pour les décimales, et des espaces pour les milliers.",
    "Use this currency":
        "Utiliser cette devise",
    "Used after a restart.":
        "Appliqué après un redémarrage.",
    "Using the key ending in {0} from {1}.":
        "Utilisation de la clé se terminant par {0} depuis {1}.",
    "Usually paid from":
        "Payé habituellement depuis",
    "Valuation {0!r} does not exist.":
        "L'évaluation {0!r} n'existe pas.",
    "Value":
        "Valeur",
    "Value by type":
        "Valeur par type",
    "Value history":
        "Historique des valeurs",
    "Value on":
        "Valeur au",
    "Values are entered by you — the app does not fetch market prices.":
        "Les valeurs sont saisies par vous — l'application ne récupère aucun cours de marché.",
    "Version":
        "Version",
    "Version {0}":
        "Version {0}",
    "Version {0} is available (you have {1}).":
        "La version {0} est disponible (vous avez la {1}).",
    "View all":
        "Tout voir",
    "vs {0}":
        "par rapport à {0}",
    "vs {0} in {1}":
        "contre {0} sur {1}",
    "Waiting for Windows Hello…":
        "En attente de Windows Hello…",
    "Warning: some allocation balances in the imported data do not add up. Check the Money / Allocations page.":
        "Attention : certains soldes d'enveloppes des données importées ne concordent pas. Vérifiez la page Argent / Enveloppes.",
    "Warning: some allocation balances in the restored data do not add up. Check the Money / Allocations page.":
        "Attention : certains soldes d'enveloppes des données restaurées ne concordent pas. Vérifiez la page Argent / Enveloppes.",
    "was unchanged":
        "est inchangé",
    "Wednesdays":
        "le mercredi",
    "Week":
        "Semaine",
    "Weekly":
        "Toutes les semaines",
    "Weekly, on {0}":
        "Toutes les semaines, {0}",
    "Well done — this goal is fully funded.":
        "Bravo — cet objectif est entièrement financé.",
    "were unchanged":
        "sont inchangées",
    "What the AI received":
        "Ce que l'IA a reçu",
    "What you have":
        "Ce que vous avez",
    "What you owe":
        "Ce que vous devez",
    "When a bank statement is imported, a line whose description contains a keyword goes to that keyword's category. Rules are learned when you change an entry's category; you can also add them here.":
        "Quand un relevé bancaire est importé, une ligne dont la description contient un mot-clé va dans la catégorie de ce mot-clé. Les règles sont apprises quand vous changez la catégorie d'une opération ; vous pouvez aussi les ajouter ici.",
    "When to lock":
        "Quand verrouiller",
    "Where is the money kept?":
        "Où l'argent est-il gardé ?",
    "Where the money went":
        "Où est passé l'argent",
    "Where your money is kept, and how much is in each account.":
        "Où se trouve votre argent, et combien sur chaque compte.",
    "Who or what":
        "Qui ou quoi",
    "Windows Hello could not confirm it's you. Try again.":
        "Windows Hello n'a pas pu confirmer votre identité. Réessayez.",
    "Windows Hello did not answer.":
        "Windows Hello n'a pas répondu.",
    "Windows Hello is not available on this computer.":
        "Windows Hello n'est pas disponible sur cet ordinateur.",
    "Windows Hello is not set up for your account. Add a PIN, fingerprint or face in Windows Settings → Accounts → Sign-in options.":
        "Windows Hello n'est pas configuré pour votre compte. Ajoutez un code PIN, une empreinte ou le visage dans Paramètres Windows → Comptes → Options de connexion.",
    "Windows Hello is ready.":
        "Windows Hello est prêt.",
    "Windows' \"Show animations in Windows\" setting is off, so Money Manager stays still as well.":
        "Le réglage Windows « Afficher les animations dans Windows » est désactivé, donc Money Manager reste immobile lui aussi.",
    "Withdraw":
        "Retirer",
    "Withdraw from {0}":
        "Retirer de {0}",
    "Withdrawal":
        "Retrait",
    "withdrawal":
        "retrait",
    "Year:":
        "Année :",
    "Yearly":
        "Tous les ans",
    "Yearly report":
        "Rapport annuel",
    "Yearly report…":
        "Rapport annuel…",
    "Yearly, {0}":
        "Tous les ans, le {0}",
    "You cannot withdraw more than the goal's recorded amount.":
        "Vous ne pouvez pas retirer plus que le montant enregistré pour l'objectif.",
    "You have the latest version ({0}).":
        "Vous avez la dernière version ({0}).",
    "You kept <b>{0}</b> of your income (income − spending; money invested counts as kept).":
        "Vous avez gardé <b>{0}</b> de vos revenus (revenus − dépenses ; l'argent investi compte comme gardé).",
    "You kept <b>{0}</b> of your income.":
        "Vous avez gardé <b>{0}</b> de vos revenus.",
    "You spent <b>{0}</b> more than your income.":
        "Vous avez dépensé <b>{0}</b> de plus que vos revenus.",
    "You will be able to reserve money for savings, bills, investments and more. Moving money between allocations never changes your total balance.":
        "Vous pourrez réserver de l'argent pour l'épargne, les factures, les investissements et plus. Déplacer de l'argent entre enveloppes ne change jamais votre solde total.",
    "Your accounts use {0}. The currency cannot be changed once accounts exist, because Money Manager never converts amounts between currencies.":
        "Vos comptes utilisent {0}. La devise ne peut plus être changée une fois des comptes créés, car Money Manager ne convertit jamais les montants d'une devise à l'autre.",
    "Your data from {0} was restored.":
        "Vos données du {0} ont été restaurées.",
    "Your financial data is stored only on this computer, in the database file shown above. Money Manager has no user account, no cloud sync and no telemetry.":
        "Vos données financières sont stockées uniquement sur cet ordinateur, dans le fichier de base de données indiqué ci-dessus. Money Manager n'a ni compte utilisateur, ni synchronisation dans le cloud, ni télémétrie.",
    "Your financial data is stored only on this computer.":
        "Vos données financières sont stockées uniquement sur cet ordinateur.",
    "Your financial overview at a glance.":
        "Vos finances en un coup d'œil.",
    "Your net worth over time appears after your first month":
        "L'évolution de votre patrimoine net apparaît après votre premier mois",
    "Your overview will live here":
        "Votre vue d'ensemble apparaîtra ici",
    "Your previous data was saved to:\n{0}":
        "Vos données précédentes ont été enregistrées dans :\n{0}",
    "{0!r} is not a valid amount.":
        "{0!r} n'est pas un montant valide.",
    "{0}\nPrevious: {1}":
        "{0}\nPrécédente : {1}",
    "{0}\nThis period: {1}\n{2}":
        "{0}\nCette période : {1}\n{2}",
    "{0} (to date)":
        "{0} (en cours)",
    "{0} added · {1} already recorded":
        "{0} ajoutées · {1} déjà enregistrées",
    "{0} could not start":
        "{0} n'a pas pu démarrer",
    "{0} failed unexpectedly. Please try again.":
        "{0} a échoué de façon inattendue. Veuillez réessayer.",
    "{0} holds {1}; cannot move {2}.":
        "{0} contient {1} ; impossible de déplacer {2}.",
    "{0} left this month":
        "{0} restants ce mois-ci",
    "{0} new · {1} already recorded · {2} cannot be read":
        "{0} nouvelles · {1} déjà enregistrées · {2} illisibles",
    "{0} of income":
        "{0} des revenus",
    "{0} of what you have":
        "{0} de ce que vous avez",
    "{0} of your total balance":
        "{0} de votre solde total",
    "{0} of {1} investments valued":
        "{0} investissements évalués sur {1}",
    "{0} of {1} up to date":
        "{0} sur {1} à jour",
    "{0} Open AI settings to set it up.":
        "{0} Ouvrez les paramètres de l'IA pour la configurer.",
    "{0} over the last {1} complete months: {2}":
        "{0} sur les {1} derniers mois complets : {2}",
    "{0} over the limit":
        "{0} au-dessus de la limite",
    "{0} per month":
        "{0} par mois",
    "{0} per year":
        "{0} par an",
    "{0} receipts attached":
        "{0} reçus joints",
    "{0} recurring entries recorded":
        "{0} opérations récurrentes enregistrées",
    "{0} recurring expenses detected, about {1} per month{2}; {3} not tracked as subscriptions.":
        "{0} dépenses récurrentes détectées, environ {1} par mois{2} ; {3} non suivies comme abonnements.",
    "{0} spending of {1} has no history in the previous {2} periods.":
        "Les dépenses {0} de {1} n'ont pas d'historique sur les {2} périodes précédentes.",
    "{0} spending of {1} is {2}x its average of {3} over the previous {4} periods.":
        "Les dépenses {0} de {1} représentent {2}x leur moyenne de {3} sur les {4} périodes précédentes.",
    "{0} the amount recorded for this goal. Your balance is not affected.":
        "{0} le montant enregistré pour cet objectif. Votre solde n'est pas touché.",
    "{0} The rest of Money Manager keeps working normally.":
        "{0} Le reste de Money Manager continue de fonctionner normalement.",
    "{0} to go":
        "Encore {0}",
    "{0} total − {1} {2}":
        "{0} au total − {1} {2}",
    "{0} transactions exported to {1}.":
        "{0} opérations exportées vers {1}.",
    "{0} vs previous period":
        "{0} par rapport à la période précédente",
    "{0} You can open Money Manager without the lock and turn it off or set Windows Hello up again.":
        "{0} Vous pouvez ouvrir Money Manager sans le verrou, puis le désactiver ou reconfigurer Windows Hello.",
    "{0} {1} compared with {2}{3}.":
        "{0} {1} par rapport à {2}{3}.",
    "{0} · adjustment {1}":
        "{0} · ajustement {1}",
    "{0} · due today":
        "{0} · échéance aujourd'hui",
    "{0} · made on {1}":
        "{0} · établi le {1}",
    "{0} · month to date ({1})":
        "{0} · mois en cours ({1})",
    "{0} · overdue by {1} {2}":
        "{0} · en retard de {1} {2}",
    "{0} · rising (no spending in the first half)":
        "{0} · en hausse (aucune dépense dans la première moitié)",
    "{0} · stable (second half vs first half of the range)":
        "{0} · stable (seconde moitié contre première moitié de la période)",
    "{0} · {1}\nNet worth: {2}\nBalance: {3}\nInvestments: {4}":
        "{0} · {1}\nPatrimoine net : {2}\nSolde : {3}\nInvestissements : {4}",
    "{0} · {1} a month":
        "{0} · {1} par mois",
    "{0} · {1} to Available":
        "{0} · {1} vers Disponible",
    "{0} · {1} {2} (second half vs first half of the range)":
        "{0} · {1} {2} (seconde moitié contre première moitié de la période)",
    "{0} · {1} {2} left":
        "{0} · reste {1} {2}",
    "{0}, month to date":
        "{0}, mois en cours",
    "{0}, year to date":
        "{0}, année en cours",
    "{0}: {1} of the monthly limit":
        "{0} : {1} de la limite mensuelle",
    "{0}: {1}, with no spending in the comparison period.":
        "{0} : {1}, sans aucune dépense sur la période de comparaison.",
    "{0}: {1}; nothing recorded in the comparison period ({2}).":
        "{0} : {1} ; rien d'enregistré sur la période de comparaison ({2}).",
    "– Not enough data":
        "– Pas assez de données",
    "“{0}” goes to {1} from now on":
        "« {0} » va dans {1} désormais",
    "“{0}” on {1} could not be recorded: {2}":
        "« {0} » du {1} n'a pas pu être enregistrée : {2}",
    "‹ Previous":
        "‹ Précédent",
    "● Fair":
        "● Correct",
    "● In progress":
        "● En cours",
    "✓ Completed":
        "✓ Terminé",
    "✓ Good":
        "✓ Bon",
    "✓ On track":
        "✓ Dans les temps",
}
