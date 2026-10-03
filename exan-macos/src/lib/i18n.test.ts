import { describe, expect, it } from "vitest";
import { translate } from "./i18n";

describe("translate", () => {
  it("fills placeholders in both languages", () => {
    expect(translate("de", "participant", { n: 3 })).toBe("Teilnehmende Person 3");
    expect(translate("en", "participant", { n: 3 })).toBe("Participant 3");
  });

  it("keeps unknown placeholders visible", () => {
    expect(translate("en", "duplicates")).toBe("Duplicate questions: {list}");
  });
});
