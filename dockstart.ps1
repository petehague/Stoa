
docker build . -t userstate -f Dockerfile-userstate
docker build . -t action -f Dockerfile-action
docker build . -t stoa -f Dockerfile
docker network create stoanet

docker run --name userstate --network stoanet userstate

docker run --name action --network stoanet action

docker run --network stoanet -p 9000:80 stoa
