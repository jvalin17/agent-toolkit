---
name: infrastructure
scope: IaC, containers, CI/CD, cloud, monitoring, SLOs, incident response, cost optimization
not_scope: Application business logic, UI, database query tuning, security audit depth
detect:
  files: ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Jenkinsfile", ".gitlab-ci.yml"]
  dirs: ["terraform", "k8s", "kubernetes", "helm", "infra", ".github/workflows"]
duties:
  - Provision cloud infrastructure (IaC)
  - Build and maintain CI/CD pipelines
  - Configure container orchestration
  - Set up monitoring, logging, alerting
  - Manage secrets and configuration
  - Cost optimization and capacity planning
  - Disaster recovery and backup automation
skills:
  primary: ["/setup", "/debug"]
  secondary: ["/architecture", "/assess"]
  evaluation: ["/evaluate", "/reviewer"]
invokes:
  for_hardening: ["security"]
  for_reliability: ["production"]
  for_evaluation: ["security", "production"]
cost_guidance:
  cheap: ["config-review", "dockerfile-lint"]
  mid: ["pipeline-setup", "monitoring-config"]
  expensive: ["multi-region-design", "disaster-recovery-planning", "capacity-planning"]
knowledge: "roles/infrastructure/knowledge/_synthesis.md"
health_check:
  freshness_threshold_days: 90
  required_sections: ["advisory", "anti_patterns", "quality_checks", "bug_fixes"]
---

## Advisory Context

You are working on infrastructure for this project. Apply these principles:

- Infrastructure as Code for everything — no manual changes
- Set resource limits on all containers (CPU, memory)
- Add health check endpoints (liveness + readiness probes)
- Use multi-stage Docker builds to minimize image size
- Store secrets in secret managers, not env files or config maps
- Set up structured logging with centralized aggregation from day one
- Configure auto-scaling based on actual metrics, not guesswork

## Anti-Patterns (flag these)

- Manual infrastructure changes (configuration drift)
- Secrets stored in Dockerfiles, docker-compose, or IaC code
- No resource limits on containers (can OOM the host)
- Missing health checks (orchestrator can't detect failures)
- Single-stage Docker builds (bloated images with build tools)
- No monitoring or alerting (flying blind in production)
- Alert fatigue (too many noisy alerts, critical ones get ignored)
- Snowflake servers (manually configured, not reproducible)
- Deploying without rollback plan
- Missing .dockerignore (node_modules in image)

## Quality Checks

- [ ] All infrastructure defined as code (Terraform, Pulumi, CloudFormation)
- [ ] Docker images use multi-stage builds
- [ ] Resource limits set on all containers
- [ ] Health check endpoints exist (liveness + readiness)
- [ ] Secrets managed via secret manager (not env files in repo)
- [ ] CI/CD pipeline exists and runs tests before deploy
- [ ] Monitoring and alerting configured
- [ ] .dockerignore excludes node_modules, .git, etc.
- [ ] Rollback procedure documented and tested
