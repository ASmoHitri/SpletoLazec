# SpletoLazec
Spletni pajek za seminarsko nalogo pri predmetu WIER  

Baza:  
docker run -dit -p 5432:5432 -e POSTGRES_DB=crawler --name db-crawler  
docker exec -it db-crawler psql -U postgres crawler