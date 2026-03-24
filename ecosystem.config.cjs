module.exports = {
  apps: [
    {
      name: 'repotalk-api',
      cwd: '/Users/jim/ProjectsSALT/repotalk',
      script: 'uvicorn',
      args: 'server.main:app --host 0.0.0.0 --port 8420 --no-access-log',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
      env: {
        PATH: process.env.PATH,
        HOME: process.env.HOME,
      },
    },
    {
      name: 'repotalk-web',
      cwd: '/Users/jim/ProjectsSALT/repotalk/web',
      script: 'npx',
      args: 'vite --port 5173',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
      env: {
        PATH: process.env.PATH,
        HOME: process.env.HOME,
      },
    },
  ],
};
