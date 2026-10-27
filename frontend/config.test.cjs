const { test } = require('node:test')
const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')

function loadConfig(value) {
  return spawnSync(process.execPath, ['-e', 'require("./next.config.js").rewrites().then(value => console.log(JSON.stringify(value)))'], {
    cwd: __dirname,
    env: { ...process.env, BACKEND_URL: value },
    encoding: 'utf8',
  })
}

test('the local proxy uses the backend port without a public API key', () => {
  const result = loadConfig('')
  assert.equal(result.status, 0)
  assert.deepEqual(JSON.parse(result.stdout), [{ source: '/api/:path*', destination: 'http://127.0.0.1:8001/api/:path*' }])
})

test('an explicit HTTPS backend is supported', () => {
  const result = loadConfig('https://api.example.invalid/')
  assert.equal(result.status, 0)
  assert.equal(JSON.parse(result.stdout)[0].destination, 'https://api.example.invalid/api/:path*')
})

test('proxy targets cannot contain credentials or non-HTTP protocols', () => {
  for (const value of ['file:///tmp/example', 'javascript:example', 'https://example:synthetic@example.invalid']) {
    assert.notEqual(loadConfig(value).status, 0, value)
  }
})

test('proxy targets reject query strings and fragments', () => {
  for (const value of ['https://example.invalid/?token=synthetic', 'https://example.invalid/#fragment']) {
    assert.notEqual(loadConfig(value).status, 0, value)
  }
})
