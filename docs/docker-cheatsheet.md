# Usefull commands

## Basic run
```
docker build . -t smnar-dashboard-lidar:v2
docker run --detach --network host -p 5000:5001 smnar-dashboard-lidar:v0
docker ps
docker exec -it <container_id> bash
docker logs <container_id>
docker stop <container_id>
docker images
docker image rm <image>
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