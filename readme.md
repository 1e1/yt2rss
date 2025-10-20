# Youtube to RSS

A hosted tool that converts YouTube URLs into podcast URLs.
This means I can watch my favourite YouTubers on a plane or in a crowded underground train.

## Quick

Copy/paste Youtube URL on `https://nas.local:2777/`, 
then add the converted URL into your podcast player. 

Enjoy! 

## Howto

Copy/paste Youtube URL like `https://youtube.com/...` to `https://nas.local:2777/...`

Some Podcast player can dislike `@`, 
so use `https://nas.local:2777/_user/...`
instead of `https://nas.local:2777/@...`. 

Otherwise read the API on `https://nas.local:2777/docs`

## Install

```bash
docker build -t yt2rss:latest .
```

```bash
docker run --name memlocal -d memcached:1-alpine memcached --memory-limit=64
docker run -d --name yt2rss -p 2777:8000 \
  -v ./_DATA:/data \
  -e YT2RSS_CHANNEL_TTL="3666" \
  yt2rss:latest
```