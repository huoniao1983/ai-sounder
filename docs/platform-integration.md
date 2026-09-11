# Live Platform Integration

The engine exposes one event path for Douyin, Kuaishou and Bilibili. Credentials stay in local runtime configuration and are never committed.

## WebSocket Connection

`POST /platform/connect`

```json
{
  "platform": "douyin",
  "config": {
    "ws_url": "wss://official-open-platform-endpoint",
    "headers": { "X-Token": "manual-authorization-token" },
    "params": { "room_id": "ROOM_ID", "app_id": "APP_ID" },
    "type_path": "type",
    "user_path": "user",
    "nickname_path": "user.nickname",
    "user_id_path": "user.id",
    "content_path": "content",
    "gift_count_path": "gift_count",
    "event_type_map": {
      "WebcastChatMessage": "danmaku",
      "WebcastGiftMessage": "gift"
    }
  }
}
```

Use the actual endpoint, headers and query parameters issued by the official platform console. Field paths are configurable because platforms can change their payload wrappers.

## Callback Forwarding

If the official product uses an HTTPS callback or a separate bridge, forward each payload to:

```text
POST /platform/callback
{"platform": "douyin", "payload": { ... }}
```

Normalized events are available at `GET /platform/events`; connection state is returned by `GET /platform/status`.

## Event Types

- `danmaku`: normal chat message
- `gift`: gift event with `gift_count`
- `enter`: viewer entered the room
- `follow`: viewer followed the host
- `like`: like event

Official binary/protobuf gateways should use the callback bridge after decoding, or provide a platform-specific decoder before `PlatformService.ingest`.
