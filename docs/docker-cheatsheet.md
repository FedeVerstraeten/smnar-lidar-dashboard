# Usefull commands

## Basic run

1. Basic necessaty commands

```
docker build . -t <image_name>:<version>smnar-dashboard-lidar:v1
docker run --detach --network host -p 5000:5001 smnar-dashboard-lidar:v0
docker ps
docker exec -it <container_id> bash
docker logs <container_id>
docker stop <container_id>
docker images
docker image rm <image>
```

2. Building image and run container

```
docker build . --tag smnar-lidar-dashboard:v1
docker run --detach --publish 8000:5000 smnar-lidar-dashboard:v1
```
3. With network sharing

```
docker build . -t smnar-dashboard-lidar:v2
docker run --d --network host -p 5000:5001 smnar-dashboard-lidar:v0
```

## Running with proxy environment variables


1. On the Docker client, create or edit the file `~/.docker/config.json` in the home directory of the user that starts containers

```
{
 "proxies":
 {
   "default":
   {
     "httpProxy": "http://192.168.1.12:3128",
     "httpsProxy": "http://192.168.1.12:3128",
     "noProxy": "*.test.example.com,.example2.com,127.0.0.0/8"
   }
 }
}
```

2. using the --env flag when you create or run the container

```
docker run --env HTTP_PROXY="http://proxy-do.smn.gov.ar:8080" --env HTTPS_PROXY="http://proxy-do.smn.gov.ar:8080"
```