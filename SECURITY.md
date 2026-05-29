# Security Hardening Guide for Production

## Critical Security Checklist

### 1. Environment Configuration
- [ ] Run `python validate_env.py` and fix all failures
- [ ] Set `ENV=production` in .env
- [ ] Generate strong JWT_SECRET (64+ chars): `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] Configure CORS_ORIGINS to your actual frontend domains (no localhost)
- [ ] Never commit .env file to version control
- [ ] Store .env in a secure secrets management system

### 2. Database Security
- [ ] Use HTTPS/SSL for all database connections
- [ ] Enable row-level security (RLS) in PostgreSQL
- [ ] Use strong database credentials
- [ ] Create separate DB users for each environment
- [ ] Enable database audit logging
- [ ] Regular backups with encryption at rest
- [ ] Use VPC/Private networking for database access

### 3. Authentication & Authorization
- [ ] Enforce HTTPS only (no HTTP in production)
- [ ] Implement account lockout after failed login attempts (5+ attempts)
- [ ] Add email verification for new signups
- [ ] Implement refresh token rotation
- [ ] Add password reset email verification
- [ ] Monitor failed authentication attempts
- [ ] Consider implementing MFA/2FA

### 4. API Security
- [ ] Enable rate limiting on all endpoints (already at 30/min on /chat)
- [ ] Add request size limits (currently 2MB default)
- [ ] Validate all input strictly (use Pydantic validation)
- [ ] Sanitize error messages to avoid information disclosure
- [ ] Use HTTPS with TLS 1.2+ minimum
- [ ] Add request signing for critical operations
- [ ] Implement CSRF protection (cookies with SameSite=Strict)
- [ ] Add request ID tracking for debugging

### 5. Data Protection
- [ ] Encrypt sensitive data at rest (passwords, API keys)
- [ ] Use bcrypt (implemented) with proper rounds (currently 12)
- [ ] Never log passwords or secrets
- [ ] Implement data retention/deletion policies
- [ ] Sanitize logs before storage
- [ ] Use HTTPS for all data in transit
- [ ] Enable encryption for database backups

### 6. Frontend Security
- [ ] Store auth token in HTTP-only, Secure cookies (not localStorage)
- [ ] Implement CSRF token validation
- [ ] Add Content Security Policy (CSP) headers
- [ ] Prevent XSS with output encoding
- [ ] Use secure headers (X-Frame-Options, X-Content-Type-Options)
- [ ] Disable browser caching for sensitive pages
- [ ] Update all dependencies regularly

### 7. Logging & Monitoring
- [ ] Enable structured logging for all security events
- [ ] Monitor failed login attempts
- [ ] Alert on suspicious patterns (brute force, DLP violations)
- [ ] Log all API accesses with user/IP/timestamp
- [ ] Implement centralized log aggregation
- [ ] Set up alerting for errors and security events
- [ ] Review logs regularly for suspicious activity

### 8. Secrets Management
- [ ] Never commit API keys or secrets
- [ ] Use environment variables or secrets vault
- [ ] Rotate API keys regularly
- [ ] Store old keys temporarily for key rotation
- [ ] Audit who has access to secrets
- [ ] Use separate keys per environment
- [ ] Implement automatic key rotation

### 9. Infrastructure Security
- [ ] Use HTTPS with valid certificate (SSL/TLS)
- [ ] Enable HSTS (HTTP Strict Transport Security)
- [ ] Use VPN or private networks for internal services
- [ ] Implement Web Application Firewall (WAF)
- [ ] Set up intrusion detection (IDS)
- [ ] Regular security patches and updates
- [ ] Use container scanning for Docker images
- [ ] Implement network segmentation

### 10. Deployment Security
- [ ] Use automated deployment with audit trail
- [ ] Require code review before production deployment
- [ ] Enable immutable deployment artifacts
- [ ] Use version pinning for dependencies
- [ ] Scan dependencies for vulnerabilities
- [ ] Test security in staging environment
- [ ] Implement blue-green deployment for safety

## Common Vulnerabilities - Already Addressed

### SQL Injection
✅ Fixed: Using SQLAlchemy ORM with parameterized queries
- All database queries use parameterized queries
- No raw SQL string concatenation

### Cross-Site Scripting (XSS)
✅ Fixed: Frontend error message sanitization
- All error messages are HTML-encoded before display
- React automatically escapes JSX content
- Input validation on all forms

### Cross-Site Request Forgery (CSRF)
✅ Fixed: SameSite cookies and CSRF token validation
- All cookies use `SameSite=Strict`
- POST/PATCH/DELETE requests include CSRF tokens
- Tokens are checked on the backend

### Authentication Bypass
✅ Fixed: Proper JWT validation and expiration
- JWT tokens explicitly verify expiration
- Access tokens expire after 24 hours
- Session/token invalidation on logout

### Rate Limiting
✅ Fixed: Rate limiting on all endpoints
- /chat: 30 requests/minute per IP
- /auth/signup: 10 requests/minute
- /auth/login: 20 requests/minute
- Conversation endpoints: 20-60 requests/minute

### Weak Passwords
✅ Fixed: OWASP-compliant password requirements
- Minimum 12 characters
- Requires uppercase, lowercase, digit, special character
- Blocked common weak passwords

### Information Disclosure
✅ Fixed: Sanitized error messages
- Error responses don't expose internal details
- Stack traces only in development mode
- Logs redact sensitive information

## Monitoring & Alerting

### Set up alerts for:
1. Failed login attempts (>5 in 15 minutes)
2. DLP policy violations
3. Unusual API usage patterns
4. Database connection errors
5. Provider API errors/rate limits
6. Failed authentication events
7. Rate limit violations
8. Database slowness (>5 seconds)

## Incident Response

### If credentials are compromised:
1. Invalidate all existing tokens
2. Force users to reset passwords
3. Rotate API keys immediately
4. Review audit logs for suspicious activity
5. Check for unauthorized access
6. Notify affected users
7. Update monitoring rules

### If application is exploited:
1. Take affected systems offline
2. Preserve logs for forensics
3. Assess scope of compromise
4. Patch vulnerability immediately
5. Review code changes
6. Retest security
7. Deploy patched version
8. Monitor for follow-up attempts

## Regular Maintenance

- [ ] Monthly: Review security logs
- [ ] Monthly: Update dependencies
- [ ] Quarterly: Run security audit
- [ ] Quarterly: Review access permissions
- [ ] Semi-annually: Penetration testing
- [ ] Annually: Security assessment
- [ ] Annually: Disaster recovery test

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
