Environment notes:
- Your shell runs inside the workspace container. The Docker daemon is shared, so
  `docker ps` also lists this container (its name ends in `-main-1`). Stopping or
  restarting it ends your session.
- If the workspace has a running application, its process ID is in
  `/tmp/application.pid`. Restart it by stopping that process and starting it again.
