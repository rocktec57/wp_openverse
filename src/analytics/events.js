import { Event } from './GoogleAnalytics'

export function CopyAttribution(type, text) {
  return new Event('Attribution Copy', type, text)
}

export function SocialMediaShare(site) {
  return new Event('Social Media', 'Share', site)
}

export function DonateLinkClick(location) {
  return new Event('Donation', 'Click', location)
}

export function DonateBannerClose() {
  return new Event('Donation', 'Close')
}
