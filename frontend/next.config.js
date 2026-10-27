/** @type {import('next').NextConfig} */
const backendUrl = (process.env.BACKEND_URL || 'http://127.0.0.1:8001').replace(/\/$/, '')
const target = new URL(backendUrl)
if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password || target.search || target.hash) {
  throw new Error('BACKEND_URL must be an http(s) address without credentials, query or fragment')
}

const nextConfig = {
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }]
  },
}

module.exports = nextConfig
