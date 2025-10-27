PHOTO-SORTER 
This container scans your photo/video library, removes duplicates, 
and sorts files into folders by year/month.

Default folders:
  /library     → full photo library
  /sorted      → output structure
  /duplicates  → duplicates
  /sorted/logs/sorter.log → log file

To run test (dry-run mode):
  docker compose up

To perform real sorting:
  Edit docker-compose.yml → set DRY_RUN=false
  Then run again:
  docker compose up
