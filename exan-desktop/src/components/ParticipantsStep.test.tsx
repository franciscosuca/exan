import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../lib/i18n";
import type { SessionView } from "../lib/types";
import { ParticipantsStep } from "./ParticipantsStep";

const mocks = vi.hoisted(() => ({
  isTauri: vi.fn(() => true),
  invoke: vi.fn(),
  act: vi.fn(),
  deleteParticipant: vi.fn(),
}));

vi.mock("@tauri-apps/api/core", () => ({ isTauri: mocks.isTauri, invoke: mocks.invoke }));

const session = {
  id: "s1",
  version: 1,
  key: { pages: [], items: [{ question: "1", answer: "B", points: 1 }], status: "done", error: null },
  participants: [
    {
      id: "p1",
      number: 1,
      name: "Anna Schmidt",
      pages: [],
      answers: [],
      status: "done",
      error: null,
      progress: { done: 0, total: 0 },
      source: "computer",
      graded: false,
      result: { score: 0, max_score: 1, percent: 0, counts: { correct: 0, incorrect: 0, review: 0, missing: 1 } },
    },
  ],
  jobs: { queued: 0, running: false, current: null },
} as unknown as SessionView;

vi.mock("../lib/store", () => ({
  useApp: () => ({ api: { deleteParticipant: mocks.deleteParticipant }, session, act: mocks.act }),
}));

const nativeConfirm = window.confirm;

function renderStep() {
  render(
    <I18nProvider initial="en">
      <ParticipantsStep onPhone={() => undefined} />
    </I18nProvider>,
  );
  return screen.getByRole("button", { name: "Delete Anna Schmidt" });
}

describe("deleting a participant", () => {
  beforeEach(() => {
    mocks.isTauri.mockReturnValue(true);
    mocks.act.mockImplementation((action: () => Promise<unknown>) => action());
    mocks.deleteParticipant.mockResolvedValue({ session });
  });

  afterEach(() => {
    window.confirm = nativeConfirm;
    vi.clearAllMocks();
  });

  it("asks with a native dialog in the desktop app and keeps the sheet when cancelled", async () => {
    // tauri-plugin-dialog replaces window.confirm with an async function; its Promise is always truthy.
    window.confirm = vi.fn(async () => false) as unknown as typeof window.confirm;
    mocks.invoke.mockResolvedValue(false);

    await userEvent.click(renderStep());

    await waitFor(() =>
      expect(mocks.invoke).toHaveBeenCalledWith("confirm_action", {
        message: "Delete this sheet?",
        okLabel: "Delete",
        cancelLabel: "Cancel",
      }),
    );
    expect(window.confirm).not.toHaveBeenCalled();
    expect(mocks.act).not.toHaveBeenCalled();
    expect(mocks.deleteParticipant).not.toHaveBeenCalled();
  });

  it("deletes the sheet once the user confirmed in the desktop app", async () => {
    mocks.invoke.mockResolvedValue(true);

    await userEvent.click(renderStep());

    await waitFor(() => expect(mocks.deleteParticipant).toHaveBeenCalledWith("p1"));
  });

  it("uses window.confirm in the browser", async () => {
    mocks.isTauri.mockReturnValue(false);
    window.confirm = vi.fn(() => false);

    await userEvent.click(renderStep());

    await waitFor(() => expect(window.confirm).toHaveBeenCalledWith("Delete this sheet?"));
    expect(mocks.invoke).not.toHaveBeenCalled();
    expect(mocks.deleteParticipant).not.toHaveBeenCalled();
  });
});
