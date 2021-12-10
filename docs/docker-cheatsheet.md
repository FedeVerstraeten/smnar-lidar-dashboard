# Usefull commands

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
