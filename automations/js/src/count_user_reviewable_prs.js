// @ts-check
/**
 * Checks the reviewable PR count for the current Github actor.
 * Return their Slack username and PR count, if found.
 *
 * @param {Object} options
 * @param {import('@octokit/rest').Octokit} options.github
 * @param {import('@actions/github')['context']} options.context
 * @param {import('@actions/core')} options.core
 */
module.exports = async ({ github, context, core }) => {
  const { GITHUB_REPOSITORY, GH_SLACK_USERNAME_MAP } = process.env
  const slackID = JSON.parse(GH_SLACK_USERNAME_MAP)[context.actor]

  if (!GITHUB_REPOSITORY || !GH_SLACK_USERNAME_MAP) {
    core.setFailed('Required dependencies were not supplied')
  }

  if (!slackID) {
    core.warning(`Slack username not found for ${context.actor}.`)
    return {}
  }

  const GET_PULL_REQUESTS = `
query ($repoOwner: String!, $repo: String!, $cursor: String) {
  repository(name:$repo, owner:$repoOwner) {
    pullRequests(states:OPEN, first:100, after: $cursor) {
      pageInfo {
        endCursor
      }
      nodes {
        author {
          login
        }
        labels(first: 100) {
          nodes {
            name
          }
        }
        isDraft
      }
    }
  }
}
`
  const ignoredLabels = [
    '🤖 aspect: text',
    '🧱 stack: documentation',
    '🟥 priority: critical',
  ]
  const [owner, repo] = GITHUB_REPOSITORY.split('/')

  try {
    let hasNextPage = true
    let cursor = null
    let reviewablePRs = []

    while (hasNextPage) {
      const result = await github.graphql(GET_PULL_REQUESTS, {
        repoOwner: owner,
        repo: repo,
        cursor: cursor,
      })

      const { nodes, pageInfo } = result.repository.pullRequests
      const validPRs = nodes.filter(
        (pr) =>
          pr.author.login === context.actor &&
          !pr.isDraft &&
          !pr.labels.nodes.some((label) => ignoredLabels.includes(label.name))
      )
      reviewablePRs.push(...validPRs)

      if (pageInfo.hasNextPage) {
        cursor = pageInfo.endCursor
      } else {
        hasNextPage = false
      }
    }

    const result = {
      pr_count: reviewablePRs.length,
      slack_id: slackID,
    }
    core.info(`Current user has ${result.pr_count} PR(s).`)
    core.setOutput('pr_count', result.pr_count)
    core.setOutput('slack_id', result.slack_id)
  } catch (error) {
    core.setFailed(`Error fetching pull requests: ${error.message}`)
  }
}
