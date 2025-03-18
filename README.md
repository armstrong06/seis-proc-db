# seis_proc_db

## Database for Yellowstone earthquake information, primarily from deep-learning methods.

## Structure
seis_proc_db/  
│  
├── app/                  # Main app code (models, services, etc.)  
│   ├── __init__.py  
│   ├── tables.py         # Database tables 
│   ├── services.py       # Business logic  
│   └── database.py       # Engine, session, base setup  
│  
├── scripts/              # Database-related scripts  
│   ├── build_tables.py   # Script to create tables  
│   └── drop_tables.py    # Script to drop tables  
│   
├── tests/                # Database-related pytests 
│   
├── config.py             # Configuration file  
└── README.md             # Documentation  