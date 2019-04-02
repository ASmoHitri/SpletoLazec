# SpletoLazec
Spletni pajek za seminarsko nalogo pri predmetu WIER  

Projekt implementira spletnega pajka, ki pri pregledovanju spleta uporablja iskanje v širino. Pajek pri tem upošteva pravila crawlanja posameznih domen, ki so definirana v robots.txt, te datoteke pa mu pomagajo tudi pri lociranju novih strani (z definicijo SiteMap-ov). SpletoLazec pri svojem delu prepoznava in beleži duplikate strani.  

## Zagon pajka
Za zagon SpletoLazca potrebujemo PostgreSQL bazo ter Python3. 

Koraki zagona:
+ Namestitev Pythonovih knjižnic: `pip3 install requirements.txt`
+ Inicializacija baze: Na bazi je treba izvesti SQL skripto  *crawler/db/init.sql*:  
    `psql -f crawler/db/init.sql -U <db_user> <db_name>`  
    **Pozor:** Baza mora imeti nastavljen timezone Europe/Berlin   (`SELECT set_config('timezone','Europe/Berlin', false)`)
+ Nastavitev konfiguracijskih parametrov:  
  Konfiguracija se nahaja v datoteki crawler/config.py. Tu je nujno nastaviti prave vrednosti za povezavo z bazo,  
  začetne URLje, ki jih program ob prvem zagonu doda v seznam še nepregledanih strani in domene po katerih naj išče
  (če želimo da pajek išče po vseh domenah nastavimo to vrednost na prazen seznam).
+ zagon programa **iz direktorija crawler**: `py main.py <število_workerjev>`  
  
### Primer postavitve in inicializacije baze z Dockerjem  
+ `docker run -dit -p 5432:5432 -e POSTGRES_DB=crawler -v db-data:/var/lib/postgresql/data --name db-crawler  postgres`
+ `docker cp crawler/db/init.sql db-crawler:/init.sql`
+ `docker exec -it db-crawler psql -f /init.sql -U postgres crawler`
