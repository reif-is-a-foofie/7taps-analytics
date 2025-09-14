# 7taps Analytics - Clean Infrastructure v2

## Overview

This is a **clean, production-ready rebuild** of the 7taps Analytics infrastructure, designed for hot-swap deployment. Built with senior engineering principles:

- **Single Responsibility**: Each component has one clear purpose
- **Proper Error Handling**: Comprehensive error management and logging
- **Clean Architecture**: Well-structured, maintainable codebase
- **Production Ready**: Comprehensive monitoring, health checks, and observability

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cloud Run     │    │   Cloud Function │    │     BigQuery    │
│   (UI + API)    │◄──►│   (Ingestion)    │◄──►│   (Analytics)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitoring    │    │     Pub/Sub      │    │  Cloud Storage  │
│   & Logging     │    │   (Event Stream) │    │  (Raw Archive)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Hot-Swap Deployment

1. **Deploy to staging**: Test all components
2. **Health check validation**: Ensure all endpoints respond
3. **Hot-swap**: Replace current deployment
4. **Rollback capability**: Instant rollback if issues

## Key Improvements

- ✅ **Consolidated GCP deployment** (no Heroku/Railway fragmentation)
- ✅ **Proper error handling** with structured logging
- ✅ **Comprehensive monitoring** and health checks
- ✅ **Clean contract structure** (5 essential contracts vs 67)
- ✅ **Production-ready configuration** with proper secrets management
- ✅ **Automated testing** and validation

