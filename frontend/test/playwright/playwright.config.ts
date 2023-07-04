import type { PlaywrightTestConfig } from "@playwright/test"

const UPDATE_TAPES = process.env.UPDATE_TAPES || "false"

/**
 * Enabling `FASTSTART` allows you to bypass running the nuxt build
 * when rapidly debugging tests locally within the container. If you
 * already have the Docker image, this is an easy way to iterate on
 * tests and do log-based debugging without needing to download the
 * enormous browser binaries (on top of the already huge Docker image
 * download).
 *
 * Note that visual-regression tests can be quite flaky when using
 * `FASTSTART`.
 */
const pwCommand =
  process.env.FASTSTART !== "false" ? "start:playwright" : "prod:playwright"

const config: PlaywrightTestConfig = {
  forbidOnly: !!process.env.CI,
  webServer: {
    command: `./node_modules/.bin/npm-run-all -p -r talkback ${pwCommand}`,
    cwd: "/frontend",
    timeout: process.env.CI ? 60_000 * 5 : 60_000 * 10, // 5 minutes in CI, 10 in other envs
    port: 8443,
    reuseExistingServer: !process.env.CI || process.env.PWDEBUG === "1",
    env: {
      API_URL: "http://localhost:49153/",
      UPDATE_TAPES: UPDATE_TAPES,
      PW: "true",
    },
  },
  use: {
    baseURL: "http://localhost:8443",
    trace: "retain-on-failure",
  },
  timeout: 60 * 1e3,
  /**
   * When updating or recreating tapes, if we have more than one worker running
   * then Talkback is liable to see multiple requests at the same time that would
   * otherwise all match the same tape. Because the requests come in all at once
   * there isn't time for Talkback to have written the tape for one of the requests
   * and then reuse it for the others. If we run with a single worker when updating
   * tapes then we can avoid this problem. Defaulting to `undefined` means the
   * Playwright default of using 1/2 of the number of CPU cores continues to work otherwise.
   */
  workers: UPDATE_TAPES === "true" ? 1 : undefined,
  expect: {
    toMatchSnapshot: {
      // If the visual regression tests are flaky, we can increase this to 0.1 or 0.2.
      maxDiffPixelRatio: 0,
    },
  },
}

export default config
