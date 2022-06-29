## 🙏 Welcome

Thank you for your interest in Openverse! We're so excited to bring new contributors into the fold in WordPress, Openverse and FOSS in general.

## ❤️ Code of Conduct

Please be aware that as a project of the WordPress Foundation, Openverse follows [the WordPress Etiquette](https://wordpress.org/about/etiquette/), a code of conduct that you should read and agree to abide by before contributing to WordPress projects. This applies to all Openverse respositories.

## 😍 Keeping in Touch

For folks who'd like to be involved in our regular development conversations, please feel free to join us in the WordPress make chat (https://make.wordpress.org/chat/). You'll find us in the #openverse channel, of course! We have weekly community meetings on Tuesdays at 15:00 UTC (https://everytimezone.com/s/d1d42c7b). All are welcome! During the meetings we discuss ongoing work and assign new issues. Attendance is not mandatory to contribute, however. Any issues labeled as "good first issue" or "help wanted" in our repositories are all up for grabs. Just add a comment with `@WordPress/openverse-maintainers` on the issue with questions or requesting the issue be assigned to you when you're ready to work on it. We also regularly discuss Openverse development issues outside the meeting times (like debugging problems we're having while working through an issue).

You can also keep in touch with [progress](https://github.com/orgs/WordPress/projects/3) and the latest updates to the project with our [WordPress contributor group](https://make.wordpress.org/openverse/).

## 📖 Translations

This document mostly covers code and documentation-based contributions. However, you may also contribute by lending a hand in translating Openverse.

An overview of Openverse translations is here: https://translate.wordpress.org/projects/meta/openverse/

A getting started guide for translating on GlotPress (the software behind `translate.wordpress.org`) is here: https://make.wordpress.org/polyglots/handbook/translating/glotpress-translate-wordpress-org/#getting-started

## 🤔 Choosing an issue

Below is a link to a list of issues that encompass a variety of different technologies, from Airflow to Django to GitHub Actions to Vue.js. You're welcome to take on any of the issues. Most require development environment set up, but some do not. Expect development environment set up to take 1 to 2 hours depending on experience and how much software you've already got installed. If you have git, a text editor/IDE, Python or Node and Docker set up, things will go a little more smoothly. If not, that's totally fine! We're here to help and our repositories all have README files that should include helpful instructions for self-guided environment set up.

Once you've picked an issue to work on, please leave a comment saying so on the issue and include `@openverse-maintainers` in the comment. That way one of us will get a notification and can assign the issue to you.

## 🤓 Initial set up

### 🪟 Note for Windows users

Windows Subsystem for Linux can be a much more versatile and familiar environment for software development on Windows. Everything from installing `git` and other dependencies to using command line tools that will be familiar to the wider community of software developers are more likely to be easier under WSL. While some parts of some Openverse projects may be able to be developed under native Windows, you will have a much smoother time with WSL as our command runners (`just` and `pnpm`) assume a unix-type environment (Linux and macOS). We would like to support native Windows development, but we do not currently have any active contributors who use Windows on a daily basis and do not have the time to spend supporting it. Likewise, many other OSS projects will not be configured to allow easy local development under Windows. WSL can help there as well.

Installation instructions for WSL on Windows 10 and 11 can be found [here on Microsoft's official documentation website](https://docs.microsoft.com/en-us/windows/wsl/install).

Of course, if you would like to contribute to Openverse by making our projects work natively on Windows, PRs for this are always welcome.

### ✍️ General set up

Skip any steps you've already completed on your own. This is meant as an exhaustive list for brand-new devs who might not have these tools yet.

1. Install `git`
    * Most Linux distributions and macOS will already have this installed. Open up your terminal app and type `which git`. If the response is anything other than `git not found` then you've already got it installed.
    * If you need to install it, follow the official instructions here: https://git-scm.com/downloads
1. Install a text editor.
    * [VSCode](https://code.visualstudio.com/) is an option with good out-of-the-box support for our entire stack.
    * [PyCharm](https://www.jetbrains.com/pycharm/) is another very popular option with lots of bells and whistles.
    * [Sublime Text](https://www.sublimetext.com/) is a minimalistic option that can get you off the ground quickly with lots of room for expansion through it's package system.
    * [vim](https://www.vim.org/) and [emacs](https://www.gnu.org/software/emacs/) are ubiquitous terminal-based options.
1. Create a GitHub account <https://github.com/signup>
1. Install pyenv or Anaconda
    * These tools make it simpler to manage multiple different versions of Python on a single machine. This is useful for contributing to multiple projects, each of which may be using a different specific version of Python.
    * Skip this if you only want to do a JavaScript issue
    * https://github.com/pyenv/pyenv
    * https://www.anaconda.com/products/individual
1. Install volta
    * Similar to pyenv/Anaconda but for Node.js
    * Skip this if you only want to do a Python issue
    * https://volta.sh/
1. Install Docker
    * Skip this if you only want to do a JavaScript issue
    * Windows with WSL: https://docs.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers#install-docker-desktop
    * All other scenarios (macOS, Linux, Native Windows): https://docs.docker.com/engine/install/
1. Choose an issue from the list below and add a comment as described in the second paragraph of the "Choosing an issue" section above
1. Fork the repository for the issue you chose
    * Go to the repository page on GitHub and find the "Fork" button in the upper corner of the page. Click this and GitHub will guide you through the process of forking the repository
1. Clone the repository into your computer
    * On the page for your fork, find the "<> Code" dropdown button. Click it and copy the link provided under the "Local" tab of the dropdown.
    * Open up your terminal app and type `git clone <copied URL>` replacing `<copied URL>` with the URL you copied from the GitHub website.
1. Follow the environment set up instructions in the README or CONTRIBUTING document in the repository
1. Start working on the issue you chose 🎉

## 🏃 Good first issues

Most of these issues are potentially able to be completed in less than 4 hours, development environment set up included. It may take significantly more or less than 4 hours depending on experience and how smoothly development environment set up goes. Unfortunately sometimes dev env set up can sometimes be tricky! In these cases it would be helpful to the Openverse project to share your experience in an issue so we can try to remove any roadblocks for future contributors. **You can make meaningful contributions to the project in the form of valuable feedback about the development experience!**

[List of Good First Issues](https://github.com/issues?q=is%3Aopen+is%3Aissue+repo%3AWordPress%2Fopenverse-catalog+repo%3AWordPress%2Fopenverse+repo%3AWordPress%2Fopenverse-api+repo%3AWordPress%2Fopenverse-frontend+label%3A%22good+first+issue%22+label%3A%22help+wanted%22+-label%3A%22%E2%9B%94+status%3A+blocked%22+-label%3A%22%F0%9F%94%92+staff+only%22+)
