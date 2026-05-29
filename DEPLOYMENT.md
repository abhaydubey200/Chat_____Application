# Production Deployment Guide

## Pre-Deployment Checklist

### 1. Code Review & Testing
- [ ] All tests pass: `pytest backend/tests/`
- [ ] No security warnings from dependency scan
- [ ] Code review completed by another developer
- [ ] Staging environment tests completed
- [ ] Load testing performed (if applicable)

### 2. Configuration Review
- [ ] Run `python backend/validate_env.py` and all checks pass
- [ ] .env file is properly configured (not in git)
- [ ] JWT_SECRET is randomly generated (64+ chars)
- [ ] CORS_ORIGINS set to actual frontend domain
- [ ] LLM provider configured and tested
- [ ] Database backup configured

### 3. Database Preparation
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] Database backups configured and tested
- [ ] Database credentials rotated
- [ ] Connection pool settings verified
- [ ] Indexes created for query optimization
- [ ] Row-level security (RLS) policies applied

### 4. Security Hardening
- [ ] Review SECURITY.md checklist
- [ ] SSL/TLS certificate obtained (not self-signed)
- [ ] HTTPS enforced (no HTTP allowed)
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Rate limiting thresholds set appropriately
- [ ] Input validation all working

### 5. Monitoring & Logging
- [ ] Structured logging configured
- [ ] Log aggregation service ready
- [ ] Monitoring dashboard created
- [ ] Alert rules configured
- [ ] Error tracking service (e.g., Sentry) integrated
- [ ] Health check endpoint tested

### 6. Infrastructure
- [ ] Server hardened (OS patches, firewall)
- [ ] Container images scanned for vulnerabilities
- [ ] Load balancer configured (if needed)
- [ ] Database backup system verified
- [ ] CDN configured (if needed)
- [ ] DNS configured and verified

## Deployment Process

### Step 1: Prepare Release
```bash
# Tag the release
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0

# Build and push container images
docker build -t myregistry/dushman-api:v1.0.0 ./backend
docker push myregistry/dushman-api:v1.0.0

docker build -t myregistry/dushman-web:v1.0.0 ./frontend
docker push myregistry/dushman-web:v1.0.0
```

### Step 2: Backup & Verify
```bash
# Backup current database
pg_dump $DATABASE_URL | gzip > db-backup-$(date +%Y%m%d-%H%M%S).sql.gz

# Verify backup
gunzip -t db-backup-*.sql.gz

# Test rollback procedures
```

### Step 3: Deploy Backend
```bash
# Using Docker Compose
docker-compose -f docker-compose.prod.yml down --remove-orphans
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Using Kubernetes
kubectl apply -f k8s/api-deployment.yaml
kubectl rollout status deployment/dushman-api
```

### Step 4: Run Migrations
```bash
# Connect to running container and apply migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Step 5: Deploy Frontend
```bash
# Deploy static assets to CDN or server
docker-compose -f docker-compose.prod.yml up -d web
# or deploy directly to hosting provider
```

### Step 6: Verify Deployment
```bash
# Check health endpoint
curl https://api.example.com/health

# Check frontend loads
curl -I https://app.example.com

# Run smoke tests
pytest tests/smoke/ -v

# Monitor logs for errors
docker-compose -f docker-compose.prod.yml logs -f api
```

### Step 7: Post-Deployment
```bash
# Monitor metrics and logs for 1 hour
# Check error rates are normal
# Verify database performance
# Test critical user workflows
```

## Rollback Procedure

If issues are discovered, rollback quickly:

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore from backup
docker-compose -f docker-compose.prod.yml up -d
psql $OLD_DATABASE_URL < db-backup-previous.sql

# Redeploy previous version
docker-compose -f docker-compose.prod.yml up -d api web
```

## Environment-Specific Configuration

### Production (.env.prod)
```
ENV=production
PROJECT_NAME=ChatHub
JWT_SECRET=<STRONG_RANDOM_KEY_64_CHARS>
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.internal:5432/chatdb
CORS_ORIGINS=https://app.example.com
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=<NVIDIA_KEY>
```

### Staging (.env.staging)
```
ENV=production
PROJECT_NAME=ChatHub-Staging
JWT_SECRET=<STAGING_KEY>
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db.internal:5432/chatdb
CORS_ORIGINS=https://staging.example.com
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=<NVIDIA_KEY>
```

## Scaling Considerations

### Vertical Scaling (Single Server)
- Increase CPU and RAM
- Increase database connection pool
- Enable Redis for caching

### Horizontal Scaling (Multiple Servers)
```yaml
# Load balancer configuration
upstream api_backend {
    least_conn;
    server api1.internal:8000;
    server api2.internal:8000;
    server api3.internal:8000;
}

server {
    listen 443 ssl http2;
    location /api {
        proxy_pass http://api_backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Database Scaling
- Use connection pooling (PgBouncer)
- Enable read replicas for read-heavy queries
- Implement query caching (Redis)
- Monitor slow queries

## Performance Optimization

### API Performance
- Enable GZIP compression (done)
- Use CDN for static assets
- Implement request caching
- Monitor response times
- Optimize database queries

### Database Performance
```sql
-- Create indexes for common queries
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM messages WHERE conversation_id = $1;
```

## Maintenance Tasks

### Daily
- Monitor error rates and logs
- Check database disk space
- Verify backups completed successfully

### Weekly
- Review security logs
- Check for dependency updates
- Performance review

### Monthly
- Security audit of logs
- Update dependencies
- Database maintenance (VACUUM, ANALYZE)

### Quarterly
- Full security assessment
- Load testing
- Disaster recovery drill
- Review and rotate secrets

## Disaster Recovery

### RTO (Recovery Time Objective): 1 hour
### RPO (Recovery Point Objective): 15 minutes

### Procedures
1. Database failure: Restore from latest backup (15 min)
2. API failure: Restart containers (5 min)
3. Frontend failure: Redeploy from CDN (10 min)
4. Region failure: Failover to secondary region (30 min)

### Testing
- Monthly: Restore from backup to test DB
- Quarterly: Full failover test
- Semi-annually: Multi-region failure test

## Support & Troubleshooting

### Common Issues

**High API Latency**
- Check database query performance
- Monitor CPU/memory usage
- Check network latency
- Review slow query logs

**Database Errors**
- Check connection pool exhaustion
- Review error logs
- Check disk space
- Monitor transaction locks

**High Memory Usage**
- Check for memory leaks in code
- Review database connection pool
- Monitor SSE stream handling
- Restart container (temporary solution)

### Useful Commands

```bash
# View real-time logs
docker-compose logs -f api

# Check container health
docker ps
docker stats

# Database connections
psql -c "SELECT count(*) FROM pg_stat_activity"

# Database size
psql -c "SELECT pg_size_pretty(pg_database_size('dbname'))"

# Slow queries
psql -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10"
```

## Contact & Escalation

- On-call engineer: [Contact Info]
- Escalation: [Escalation Contacts]
- Communication channel: [Slack/Discord/etc]
