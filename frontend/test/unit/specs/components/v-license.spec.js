import { screen } from "@testing-library/vue"

import { render } from "~~/test/unit/test-utils/render"

import VLicense from "~/components/VLicense/VLicense.vue"

describe("VLicense", () => {
  let options = {
    props: {
      license: "by",
    },
  }

  it("should render the license name and icons", () => {
    const { container } = render(VLicense, options)
    const licenseName = screen.getByLabelText("Attribution")
    expect(licenseName).toBeInTheDocument()
    const licenseIcons = container.querySelectorAll("svg")
    expect(licenseIcons).toHaveLength(2) // 'CC' and 'BY' icons
  })

  it("should render only the license icons", () => {
    options.props.hideName = true
    const { container } = render(VLicense, options)
    const licenseName = screen.queryByText("CC BY")
    expect(licenseName).not.toBeVisible()
    const licenseIcons = container.querySelectorAll("svg")
    expect(licenseIcons).toHaveLength(2)
  })

  it("should have background filled with black text", () => {
    options.props.bgFilled = true
    const { container } = render(VLicense, options)
    const licenseIcons = container.querySelectorAll("svg")
    expect(licenseIcons).toHaveLength(2)
    licenseIcons.forEach((icon) => {
      expect(icon).toHaveClass("bg-filled", "text-black")
    })
  })
})
