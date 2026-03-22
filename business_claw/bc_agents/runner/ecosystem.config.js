module.exports = {
  apps: [
    {
      name: 'bc-agent-runner',
      script: './runner/daemon.py',
      interpreter: 'python3',
      args: '--daemon --poll-interval=5',

      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',

      env: {
        'FRAPPE_SITE': 'localhost',
        'BC_AGENT_MODE': 'production',
        'BC_LOG_LEVEL': 'INFO',
        'BC_POLL_INTERVAL': '5',
      },

      env_development: {
        'FRAPPE_SITE': 'localhost',
        'BC_AGENT_MODE': 'development',
        'BC_LOG_LEVEL': 'DEBUG',
        'BC_POLL_INTERVAL': '10',
      },

      env_staging: {
        'FRAPPE_SITE': 'staging.example.com',
        'BC_AGENT_MODE': 'staging',
        'BC_LOG_LEVEL': 'INFO',
        'BC_POLL_INTERVAL': '5',
      },

      error_file: './logs/agent-runner-error.log',
      out_file: './logs/agent-runner-out.log',
      log_file: './logs/agent-runner-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      merge_logs: true,
      kill_timeout: 10000,
      restart_delay: 5000,

      max_restarts: 10,
      min_uptime: '10s',

      listen_timeout: 8000,
      wait_ready: true,
      instance_var: 'INSTANCE_ID',

      source_map_support: false,

      shutdown_with_message: true,
    },
    {
      name: 'bc-agent-runner-workers',
      script: './runner/worker_pool.py',
      interpreter: 'python3',
      args: '--workers=4',

      instances: 4,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',

      env: {
        'FRAPPE_SITE': 'localhost',
        'BC_WORKER_MODE': 'production',
        'BC_LOG_LEVEL': 'INFO',
      },

      env_development: {
        'FRAPPE_SITE': 'localhost',
        'BC_WORKER_MODE': 'development',
        'BC_LOG_LEVEL': 'DEBUG',
      },

      error_file: './logs/worker-error.log',
      out_file: './logs/worker-out.log',
      log_file: './logs/worker-combined.log',

      kill_timeout: 5000,
      restart_delay: 3000,

      max_restarts: 20,
      min_uptime: '5s',

      wait_ready: false,
    },
  ],

  deploy: {
    production: {
      user: 'frappe',
      host: 'localhost',
      ref: 'origin/main',
      repo: 'git@github.com:business-claw/business-claw.git',
      path: '/opt/business_claw',
      'pre-deploy-local': 'echo "Pre-deploy local"',
      'post-deploy': 'cd runner && pm2 reload ecosystem.config.js --env production',
    },
    staging: {
      user: 'frappe',
      host: 'staging.example.com',
      ref: 'origin/develop',
      repo: 'git@github.com:business-claw/business-claw.git',
      path: '/opt/business_claw_staging',
      'post-deploy': 'cd runner && pm2 reload ecosystem.config.js --env staging',
    },
  },
};
