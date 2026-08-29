# Product → Role Mapping

> How our 19 roles would build each product
> Roles marked with * are primary/lead for that product

## 1. Dematic (Warehouse Automation)

| Role | Responsibility |
|------|---------------|
| **System Architect*** | WMS/WES/WCS layered architecture, hardware abstraction layer, edge/cloud hybrid design, PLC protocol integration patterns |
| **Embedded/IoT*** | PLC communication, conveyor/robot control protocols, real-time hardware commands, sensor data acquisition, fault-tolerant device drivers |
| **Backend Engineer*** | WMS business logic (inventory, orders, fulfillment), ERP integration APIs (SAP, Oracle), event-driven orchestration engine |
| **Frontend Developer** | SCADA dashboards, real-time warehouse visualization, operator control panels, monitoring UIs |
| **DBA** | Inventory database (millions of SKUs × locations), transaction isolation for concurrent picks, time-series for throughput metrics |
| **Data Engineer** | Real-time telemetry pipeline from equipment, throughput analytics, predictive maintenance data pipeline |
| **AI/ML Engineer** | Pick path optimization, demand forecasting, predictive maintenance models, wave planning optimization |
| **Infrastructure Engineer** | Edge computing setup (local control survives cloud outage), cloud platform, monitoring/alerting for equipment health |
| **Security Engineer** | Industrial network security, access control for equipment commands, audit logging for safety compliance |
| **Production Engineer** | Simulate warehouse operations, verify equipment responds correctly, test failover scenarios |
| **QA Engineer** | Hardware-in-loop testing, simulation test environments, fault injection testing |
| **Code Health Engineer** | Vendor-agnostic abstraction layer maintenance, equipment driver compatibility |
| **Requirements Engineer** | Warehouse-specific configuration tracking (every warehouse is different), equipment spec compliance |
| **Research Engineer** | New robotics platforms, AMR vendor evaluation, industry 4.0 standards |
| **Legal & Compliance** | Industrial safety regulations (OSHA), equipment certification, data retention for safety audits |

**Skills used:** `/architecture` (layered system design), `/implementation` (WMS logic), `/debug_tool` (equipment communication issues), `/setup` (edge deployment), `/evaluate` (system reliability)

---

## 2. Spades Game (Competitive Multiplayer Card Game)

| Role | Responsibility |
|------|---------------|
| **Game Developer*** | Authoritative game server (state machine for deal→bid→play→score), card game rules engine, AI opponents (bidding strategy + trick play), replay system |
| **Backend Engineer*** | Matchmaking (ELO/Glicko-2 rating), lobby/room system, user accounts, leaderboards, match history persistence, WebSocket server |
| **Frontend Developer** | Card UI (animations, drag-drop), game table layout, bidding interface, chat, leaderboard screens |
| **iOS Developer** | Native iOS app with card animations, haptic feedback on plays, push notifications for turns |
| **Android Developer** | Native Android app, material design card UI, FCM notifications |
| **DBA** | Player stats schema (win rate, bid accuracy, bags), match history, rating calculations |
| **AI/ML Engineer** | Game AI — bidding strategy model, trick-play optimization, partner-aware team play AI, difficulty levels |
| **Security Engineer** | Anti-cheat (hidden card information leakage prevention), collusion detection, WebSocket security |
| **Production Engineer** | Play full games end-to-end, verify scoring, test reconnection mid-hand, load test concurrent games |
| **QA Engineer** | Edge cases (nil bids, bags penalty, renege detection), disconnection scenarios, AI behavior testing |
| **Research Engineer** | Card game AI approaches, competitive game matchmaking algorithms, real-time networking patterns |
| **Requirements Engineer** | Spades rule variants tracking, tournament format specs |
| **Legal & Compliance** | Gambling law implications (if real money), age restrictions by country |

**Skills used:** `/implementation` (game server), `/architecture` (networking model), `/debug_tool` (desync issues), `/verify` (rule correctness)

---

## 3. Age of Empires (Desktop + iOS)

| Role | Responsibility |
|------|---------------|
| **Game Developer*** | Game engine (loop, rendering, physics), deterministic simulation, pathfinding (A*/flow-field for hundreds of units), ECS architecture, AI (strategic + tactical), map generation, replay system, mod support/scenario editor |
| **System Architect*** | Lockstep networking architecture (desktop), client-server for mobile, deterministic simulation guarantees, cross-platform architecture |
| **iOS Developer*** | Touch control system for RTS (selection, scrolling, commanding groups — completely different from mouse/keyboard), mobile-optimized simulation (reduced unit counts, simplified pathfinding), battery/thermal management |
| **Backend Engineer** | Matchmaking server, player profiles, ranked ladders, campaign progress sync, mod distribution |
| **Frontend Developer** | Desktop UI (menus, tech tree viewer, minimap, HUD), lobby interface |
| **AI/ML Engineer** | Civilization AI (build order strategy, army composition, attack timing), unit micro-management AI, difficulty scaling |
| **DBA** | Player rankings, match history, civilization stats, mod metadata |
| **Infrastructure Engineer** | Game server hosting, matchmaking infrastructure, mod workshop hosting |
| **Security Engineer** | Anti-cheat (memory scanning, replay validation), save file integrity |
| **Production Engineer** | Play full matches on all platforms, verify deterministic sync, test 8-player multiplayer, performance profiling |
| **QA Engineer** | Civilization balance testing, pathfinding edge cases, desync detection tests, platform-specific bugs |
| **Code Health Engineer** | Engine performance regression tracking, deterministic simulation verification across compiler versions |
| **Research Engineer** | RTS design patterns, "1500 archers on 28.8" networking paper, modern pathfinding algorithms, mobile RTS adaptations |
| **Requirements Engineer** | 30+ civilization specs, tech tree tracking, balance requirements |
| **Legal & Compliance** | Age ratings (ESRB/PEGI), in-app purchase regulations for mobile |

**Skills used:** `/architecture` (engine + networking), `/implementation` (game systems), `/debug_tool` (desync, pathfinding), `/evaluate` (performance), `/explore` (existing engine patterns)

---

## 4. Instagram Lightweight

| Role | Responsibility |
|------|---------------|
| **Backend Engineer*** | REST API (auth, posts, feed, likes, comments, follows), media upload handling, feed generation (fan-out-on-write vs read), notifications, social graph queries |
| **Frontend Developer*** | Feed UI (infinite scroll, image grid), post creation (upload, caption, filters), profile pages, stories viewer, responsive design |
| **iOS Developer** | Native iOS with camera integration, filters, share extension, push notifications |
| **Android Developer** | Native Android with camera, share, FCM notifications |
| **DBA** | Social graph schema (follows as directed graph), post/like/comment tables, index strategy for feed queries, counter caching for like counts |
| **Data Engineer** | Media processing pipeline (resize, compress, thumbnail, strip EXIF — async with queue), CDN cache invalidation |
| **Infrastructure Engineer** | Object storage (S3/R2) for media, CDN configuration, auto-scaling for upload spikes |
| **Security Engineer** | Auth (OAuth/JWT), image sanitization (EXIF stripping for privacy), content upload validation, CSRF/XSS prevention |
| **Production Engineer** | Test full flow (signup→post→feed→like→comment), verify media processing, check feed generation speed, image loading performance |
| **QA Engineer** | Feed ordering tests, media upload edge cases (large files, corrupt images, slow network), privacy settings verification |
| **System Architect** | Feed generation strategy decision (fan-out-on-write for MVP), caching strategy, media pipeline architecture |
| **Code Health Engineer** | Feed query performance monitoring, storage cost tracking |
| **Requirements Engineer** | Feature scoping (MVP: posts, feed, follow, like — NOT stories, reels, DMs initially) |
| **Research Engineer** | How Instagram actually works (fan-out, Cassandra, CDN strategy), image processing libraries |
| **Legal & Compliance** | Privacy policy (photo metadata, location data), GDPR (right to delete), content moderation obligations |

**Skills used:** `/requirements` (scope MVP), `/architecture` (feed design), `/implementation` (API + UI), `/setup` (media pipeline), `/precommit` (quality gate)

---

## 5. Reel-to-Text App

| Role | Responsibility |
|------|---------------|
| **AI/ML Engineer*** | Speech-to-text pipeline (Whisper model selection, GPU inference setup), language detection, speaker diarization (pyannote.audio), post-processing (punctuation restoration, filler removal) |
| **Backend Engineer*** | Job queue for async transcription, video URL ingestion (yt-dlp), audio extraction (FFmpeg), result storage, REST API for submissions/results |
| **Frontend Developer** | Upload UI, URL paste input, transcription viewer with timestamps, download buttons (SRT/VTT/TXT), progress indicators |
| **Data Engineer** | Audio extraction pipeline (video → 16kHz mono WAV), batch processing for bulk transcription |
| **Infrastructure Engineer** | GPU instance provisioning (Modal/RunPod/Lambda), job queue infrastructure, storage for temporary video/audio files |
| **iOS Developer** | Mobile app with video picker, share extension ("transcribe this reel" from other apps) |
| **Android Developer** | Mobile app with video picker, share intent handler |
| **Security Engineer** | Video content handling (don't store user videos longer than needed), API rate limiting |
| **Production Engineer** | Test with noisy audio, multiple languages, background music, overlapping speakers, measure accuracy |
| **QA Engineer** | Edge cases (silent video, music-only, very long/short clips, multiple languages in one video) |
| **Research Engineer** | Whisper model benchmarks (speed vs accuracy), alternative STT services comparison, diarization approaches |
| **Requirements Engineer** | Supported languages, accuracy targets, supported video formats/sources |
| **Legal & Compliance** | TOS implications of scraping videos from platforms, content storage policies, GDPR for processed data |

**Skills used:** `/implementation` (pipeline), `/architecture` (GPU serving), `/setup` (infrastructure), `/debug_tool` (accuracy issues), `/evaluate` (transcription quality)

---

## 6. TikTok

| Role | Responsibility |
|------|---------------|
| **System Architect*** | Overall platform architecture (video pipeline, recommendation engine, social graph, content moderation, ads platform), multi-region design |
| **AI/ML Engineer*** | Recommendation engine (candidate generation → fine ranking), content moderation classifiers (violence, nudity, misinformation in video+audio), audio fingerprinting for copyright |
| **Backend Engineer*** | Video upload API, social features (follow, like, comment, duet/stitch), notifications, creator analytics API, sound library management |
| **Frontend Developer** | Full-screen vertical video player, swipe-to-next feed, in-app video editor (filters, effects, text overlays, green screen), comments/chat |
| **iOS Developer** | Native camera with AR filters (on-device ML), video recording/editing, share extension, background audio |
| **Android Developer** | Same as iOS — camera, AR, editing, background playback |
| **Data Engineer*** | Real-time event pipeline (Flink/Kafka — every scroll, watch duration, replay feeds back), data lake (Delta Lake), engagement analytics pipeline |
| **DBA** | Social graph (billions of edges), video metadata, comment threads, high-write counters (views, likes) |
| **Infrastructure Engineer*** | Global CDN for video delivery, adaptive bitrate streaming (HLS/DASH), GPU clusters for ML, transcoding farm, multi-region deployment |
| **Security Engineer** | Content moderation pipeline, creator account security, API abuse prevention, data privacy (COPPA for minors) |
| **Production Engineer** | Feed latency testing, video upload→processing→available timing, transcoding verification, CDN cache behavior |
| **QA Engineer** | Feed ranking quality testing, video playback across devices/networks, moderation accuracy testing |
| **Data Scientist** | Engagement metrics design, A/B test framework for ranking experiments, content trend analysis |
| **Code Health Engineer** | Recommendation model versioning, pipeline reliability, technical debt in fast-moving codebase |
| **Requirements Engineer** | Feature parity across platforms, creator tools spec tracking |
| **Research Engineer** | Recommendation algorithm research (deep learning architectures), video compression advances, edge AI for on-device inference |
| **Legal & Compliance*** | COPPA compliance (children), content moderation laws (DSA in EU, Section 230 in US), music licensing, data residency, country-specific bans/restrictions |

**Skills used:** ALL skills — this is a mega-scale system. `/architecture` (system design), `/implementation` (every component), `/evaluate` (quality at scale), `/assess` (architecture fitness)

---

## 7. YouTube Music

| Role | Responsibility |
|------|---------------|
| **Backend Engineer*** | Audio catalog API, playlist CRUD, playback queue management, search API, user library management, offline sync protocol |
| **AI/ML Engineer*** | Music recommendation (collaborative filtering + content-based + context-aware), personalized mixes, radio station generation, audio fingerprinting ("what song is this?"), genre/mood classification |
| **Frontend Developer** | Web player (gapless playback, queue UI, playlist management, search, lyrics display), responsive design |
| **iOS Developer** | Background audio playback, lock screen controls, CarPlay, AirPlay/Chromecast, offline downloads with DRM, Siri integration |
| **Android Developer** | Background playback, notification controls, Android Auto, Chromecast, offline with DRM, Bluetooth metadata |
| **Data Engineer** | Streaming analytics pipeline (every play counted for royalties — must be perfectly accurate), listening history pipeline, recommendation feature pipeline |
| **DBA** | Music catalog schema (tracks, albums, artists, labels — complex many-to-many relationships), playlist storage, play count aggregation |
| **Infrastructure Engineer** | Audio CDN (edge caching for popular tracks, origin for long tail), adaptive streaming infrastructure, multi-region deployment |
| **System Architect** | Audio delivery architecture (gapless playback requires precise buffering), DRM architecture, offline sync design, cross-device state sync |
| **Security Engineer** | DRM implementation (Widevine/FairPlay), API authentication, content access control, piracy prevention |
| **Production Engineer** | Test gapless playback across devices, verify offline sync, check Bluetooth/AirPlay/Chromecast casting, measure streaming quality |
| **QA Engineer** | Playback edge cases (network drop mid-song, switching audio output, seek in long tracks), shuffle algorithm fairness testing, cross-device sync |
| **Data Scientist** | Engagement metrics, listening pattern analysis, skip rate analysis for recommendation tuning, A/B testing playlist generation |
| **Research Engineer** | Audio recommendation research, music information retrieval, gapless playback techniques, codec comparison (AAC vs Opus vs FLAC) |
| **Requirements Engineer** | Feature parity across platforms, offline capability specs, audio quality tier definitions |
| **Legal & Compliance*** | Music licensing (per-country rights), royalty tracking and reporting (legal requirement), DMCA compliance, territory restrictions |

**Skills used:** `/architecture` (streaming + DRM), `/implementation` (player + API), `/debug_tool` (playback issues), `/setup` (CDN + infrastructure), `/evaluate` (audio quality)

---

## 8. Personal Netflix (Self-Hosted Video Streaming)

| Role | Responsibility |
|------|---------------|
| **Backend Engineer*** | Media library scanner (filesystem watch → metadata matching via TMDB/TVDB), transcoding engine wrapper (FFmpeg command construction), streaming server (HLS/DASH segment serving), user management, playback state sync, subtitle handling |
| **Frontend Developer*** | Video player (adaptive streaming, subtitle overlay, seek, resume), library browsing UI (poster grid, search, genres), TV-optimized UI (10-foot interface for smart TV) |
| **System Architect** | Transcoding decision engine (direct play vs remux vs full transcode based on client capabilities), hardware acceleration abstraction (Intel/NVIDIA/AMD/Apple) |
| **Data Engineer** | Media scanning pipeline (filename parsing → metadata matching → artwork fetching), transcoding job pipeline |
| **iOS Developer** | iOS/tvOS app with AirPlay, picture-in-picture, offline downloads |
| **Android Developer** | Android/Android TV app with Chromecast, picture-in-picture |
| **DBA** | Media metadata schema, user watch history, playback positions per user per device |
| **Infrastructure Engineer** | Self-hosted deployment (Docker Compose), reverse proxy for remote access, hardware transcoding setup, DLNA/UPnP for local devices |
| **AI/ML Engineer** | Watch history-based recommendations (optional — "because you watched X") |
| **Security Engineer** | Remote access security (HTTPS, auth), DRM for downloaded content, multi-user access control |
| **Production Engineer** | Test playback across devices (web, TV, mobile, Chromecast), verify transcoding quality, test subtitle rendering, remote access through NAT |
| **QA Engineer** | Codec compatibility matrix testing (input format × output format × device), HDR→SDR tone mapping verification, edge cases (corrupt files, missing metadata, non-standard containers) |
| **Code Health Engineer** | FFmpeg version compatibility, dependency upgrades (codec libraries) |
| **Research Engineer** | Existing solutions analysis (Jellyfin architecture, Plex features), transcoding optimization, hardware acceleration options |
| **Requirements Engineer** | Supported devices/platforms, codec support matrix, feature comparison with Plex/Jellyfin |
| **Embedded/IoT** | Smart TV app development (limited runtime environments), Roku/Fire TV platform constraints |

**Skills used:** `/explore` (Jellyfin/Plex codebase), `/architecture` (transcoding engine), `/implementation` (scanner + player), `/setup` (Docker deployment), `/debug_tool` (codec issues)

---

## Summary: Role Activity Across Products

| Role | Products Active In (out of 8) |
|------|------|
| Backend Engineer | 8/8 |
| Production Engineer | 8/8 |
| QA Engineer | 8/8 |
| Security Engineer | 8/8 |
| Research Engineer | 8/8 |
| Frontend Developer | 7/8 |
| System Architect | 7/8 |
| Requirements Engineer | 7/8 |
| Infrastructure Engineer | 7/8 |
| DBA | 7/8 |
| iOS Developer | 7/8 |
| Android Developer | 7/8 |
| AI/ML Engineer | 7/8 |
| Code Health Engineer | 6/8 |
| Legal & Compliance | 7/8 |
| Data Engineer | 6/8 |
| Data Scientist | 3/8 |
| Game Developer | 2/8 |
| Embedded/IoT | 2/8 |
