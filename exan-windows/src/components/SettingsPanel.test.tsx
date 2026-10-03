import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../lib/i18n";
import type { BuiltinModel, RuntimeView, Settings } from "../lib/types";
import { SettingsPanel } from "./SettingsPanel";

const mocks = vi.hoisted(() => ({
  api: {
    settings: vi.fn(),
    catalog: vi.fn(),
    runtime: vi.fn(),
    models: vi.fn(),
    pull: vi.fn(),
    cancelPull: vi.fn(),
    deleteModel: vi.fn(),
    saveSettings: vi.fn(),
  },
  confirmAction: vi.fn(),
}));

vi.mock("../lib/store", () => ({
  useApp: () => ({ api: mocks.api, run: (action: () => Promise<unknown>) => action().catch(() => undefined) }),
}));
vi.mock("../lib/bridge", () => ({ confirmAction: mocks.confirmAction, openHelp: vi.fn() }));

const settings: Settings = {
  runtime: "builtin",
  ollama_url: "http://127.0.0.1:11434",
  openai_url: "http://127.0.0.1:1234/v1",
  model: "small",
  extraction_mode: "auto",
  max_image_side: 1600,
  request_timeout: 300,
  language: "en",
};

function model(id: string, extra: Partial<BuiltinModel> = {}): BuiltinModel {
  return {
    id,
    label: id.toUpperCase(),
    vendor: "Vendor",
    params: "1B",
    mode: "ocr",
    recommended: false,
    license: "Apache-2.0",
    homepage: "",
    min_ram_gb: 4,
    download_bytes: 281_687_936,
    downloaded_bytes: 0,
    installed: false,
    notes: { en: "Notes" },
    summary: { en: "Summary" },
    source: "huggingface.co/org/repo",
    ...extra,
  };
}

const runtime: RuntimeView = { kind: "builtin", url: "", reachable: true, version: "b11376", models: [], error: null, model: "small", model_installed: true, pull: {} };

function renderPanel() {
  render(
    <I18nProvider initial="en">
      <SettingsPanel onClose={vi.fn()} onChanged={vi.fn()} />
    </I18nProvider>,
  );
}

describe("SettingsPanel with the built-in runtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.api.settings.mockResolvedValue(settings);
    mocks.api.catalog.mockResolvedValue([]);
    mocks.api.runtime.mockResolvedValue(runtime);
    mocks.api.models.mockResolvedValue([
      model("small", { recommended: true, installed: true }),
      model("other", { installed: true }),
      model("big", { download_bytes: 2_774_658_784 }),
    ]);
    mocks.api.saveSettings.mockImplementation(async (patch: Partial<Settings>) => ({ ...settings, ...patch }));
    mocks.api.pull.mockResolvedValue({ state: "running", model: "big", completed: 0, total: 2_774_658_784 });
  });

  it("downloads more models only after consent", async () => {
    renderPanel();
    const list = await screen.findByTestId("builtin-models");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument(); // no server address for the built-in runtime
    const download = within(list).getByRole("button", { name: /Download/ });
    expect(download).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /downloads models from Hugging Face/ }));
    await userEvent.click(download);
    await waitFor(() => expect(mocks.api.pull).toHaveBeenCalledWith("big"));
    expect(await screen.findByTestId("pull-progress")).toHaveTextContent("Downloading BIG: 0 MB of 2.8 GB (0 %)");
  });

  it("switches between installed models and removes one after confirmation", async () => {
    renderPanel();
    const list = await screen.findByTestId("builtin-models");
    expect(within(list).getAllByText("Active")).toHaveLength(1);
    await userEvent.click(within(list).getByRole("button", { name: "Use" }));
    await waitFor(() => expect(mocks.api.saveSettings).toHaveBeenCalledWith({ model: "other" }));

    mocks.confirmAction.mockResolvedValueOnce(false);
    await userEvent.click(within(list).getAllByRole("button", { name: "Remove" })[1]);
    expect(mocks.confirmAction).toHaveBeenCalledWith("Remove OTHER from this computer? This frees 282 MB.", "Remove", "Cancel");
    expect(mocks.api.deleteModel).not.toHaveBeenCalled();

    mocks.confirmAction.mockResolvedValueOnce(true);
    mocks.api.deleteModel.mockResolvedValue([model("small", { recommended: true, installed: true }), model("other"), model("big")]);
    await userEvent.click(within(list).getAllByRole("button", { name: "Remove" })[1]);
    await waitFor(() => expect(mocks.api.deleteModel).toHaveBeenCalledWith("other"));
  });

  it("keeps the Ollama settings when Ollama is selected", async () => {
    mocks.api.settings.mockResolvedValue({ ...settings, runtime: "ollama", model: "qwen2.5vl:3b" });
    mocks.api.runtime.mockResolvedValue({ ...runtime, kind: "ollama", url: settings.ollama_url, version: "0.35.1" });
    renderPanel();
    expect(await screen.findByDisplayValue("http://127.0.0.1:11434")).toBeInTheDocument();
    expect(screen.queryByTestId("builtin-models")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Built in (recommended)" })).not.toBeChecked();
  });
});
