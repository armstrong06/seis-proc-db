# seis_proc_db

## Database for Yellowstone earthquake information, primarily from deep-learning methods.

## Structure
<pre>
seis-proc-db/  
│  
├── src/                  # use src layout  
|   └──seis_proc_db/      # Main app code (models, services, etc.)  
│       ├── __init__.py    
│       ├── config.py         # Configuration file   
│       ├── tables.py         # Database tables   
│       ├── services.py       # Business logic    
│       └── database.py       # Engine, session, base setup    
│  
├── scripts/              # Database-related scripts   
│   ├── build_tables.py   # Script to create tables   
│   └── drop_tables.py    # Script to drop tables   
│    
├── tests/                # seis_proc_db pytests  
|   ├── __init__.py 
│   ├── conftest.py       # To share fixtures across multiple files (e.g., building a db session)
│   └── test_tables.py    # Tests for seis_proc_db.tables
|   
└── README.md             # Documentation   
</pre>