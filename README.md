# seis_proc_db

## Database for Yellowstone earthquake information, primarily from deep-learning methods.

## Structure (from ChatGPT)
seis_proc_db/
│
├── app/                  # Main app code (models, services, etc.)
│   ├── __init__.py
│   ├── models.py         # Database models (tables)
│   ├── services.py       # Business logic
│   └── database.py       # Engine, session, base setup
│
├── db/                   # Database-related scripts
│   ├── build_tables.py   # Script to create tables
|   └── drop_tables.py    # Script to drop tables
│
├── config.py             # Configuration file
├── requirements.txt      # Dependencies
└── README.md             # Documentation