import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../lib/i18n";
import type { BuiltinModel, PullView, RuntimeView } from "../lib/types";
import { SetupWizard } from "./SetupWizard";

const api = vi.hoisted(() => ({
  models: vi.fn(),
  saveSettings: vi.fn(),
  pull: vi.fn(),
  cancelPull: vi.fn(),
  runtime: vi.fn(),
}));

vi.mock("../lib/store", () => ({
  useApp: () => ({ api, run: (action: () => Promise<unknown>) => action().catch(() => undefined) }),
}));

function model(id: string, extra: Partial<BuiltinModel> = {}): BuiltinModel {
  return {
    id,
    label: id.toUpperCase(),
    vendor: "Vendor",
    params: "1B",
    mode: "ocr",
    recommended: false,
    license: "Apache-2.0",
    homepage: "https://huggingface.co/x",
    min_ram_gb: 4,
    download_bytes: 281_687_936,
    downloaded_bytes: 0,
    installed: false,
    notes: { en: `Notes for ${id}`, de: `Hinweise zu ${id}` },
    summary: { en: `Summary of ${id}`, de: `Kurz: ${id}` },
    source: "huggingface.co/org/repo",
    ...extra,
  };
}

function runtimeView(pull: PullView = {}, modelId = ""): RuntimeView {
  return { kind: "builtin", url: "", reachable: true, version: "b11376", models: [], error: null, model: modelId, model_installed: false, pull };
}

function renderWizard(runtime = runtimeView(), onReady = vi.fn()) {
  render(
    <I18nProvider initial="en">
      <SetupWizard runtime={runtime} onReady={onReady} onAdvanced={vi.fn()} />
    </I18nProvider>,
  );
  return onReady;
}

describe("SetupWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.models.mockResolvedValue([model("small", { recommended: true }), model("ocr-big", { download_bytes: 1_817_539_616 })]);
    api.saveSettings.mockImplementation(async (patch: object) => patch);
    // The engine reports the size only once the download has started; the catalog size is shown until then.
    api.pull.mockResolvedValue({ state: "running", model: "small", status: "starting", completed: null, total: null });
  });

  it("preselects the recommended model and downloads only after consent", async () => {
    renderWizard();
    const recommended = await screen.findByRole("radio", { name: /SMALL/ });
    expect(recommended).toBeChecked();
    const download = screen.getByRole("button", { name: "Download and use" });
    expect(download).toBeDisabled();
    expect(screen.getByText(/I agree that Exan downloads 282 MB from Hugging Face \(huggingface\.co\)/)).toBeInTheDocument();

    await userEvent.click(download);
    expect(api.pull).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(download);
    await waitFor(() => expect(api.pull).toHaveBeenCalledWith("small"));
    expect(api.saveSettings).toHaveBeenCalledWith({ runtime: "builtin", model: "small" });
    expect(await screen.findByTestId("pull-progress")).toHaveTextContent("Downloading SMALL: 0 MB of 282 MB (0 %)");
  });

  it("preselects the model chosen in the installer when its download did not finish", async () => {
    renderWizard(runtimeView({}, "ocr-big"));
    expect(await screen.findByRole("radio", { name: /OCR-BIG/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /SMALL/ })).not.toBeChecked();
  });

  it("downloads the model the user picked", async () => {
    renderWizard();
    await userEvent.click(await screen.findByRole("radio", { name: /OCR-BIG/ }));
    expect(screen.getByText(/downloads 1\.8 GB/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Download and use" }));
    await waitFor(() => expect(api.pull).toHaveBeenCalledWith("ocr-big"));
  });

  it("uses an installed model without asking to download", async () => {
    api.models.mockResolvedValue([model("small", { recommended: true, installed: true })]);
    const onReady = renderWizard();
    await userEvent.click(await screen.findByRole("button", { name: "Use this model" }));
    await waitFor(() => expect(onReady).toHaveBeenCalled());
    expect(api.pull).not.toHaveBeenCalled();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("shows a running download and lets the user cancel it", async () => {
    api.cancelPull.mockResolvedValue({ state: "cancelled", model: "small" });
    renderWizard(runtimeView({ state: "running", model: "small", completed: 140_843_968, total: 281_687_936 }, "small"));
    expect(await screen.findByTestId("pull-progress")).toHaveTextContent("(50 %)");
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(api.cancelPull).toHaveBeenCalled());
    expect(await screen.findByText("Download cancelled. It continues next time.")).toBeInTheDocument();
  });

  it("offers to resume a partial download and shows download errors", async () => {
    api.models.mockResolvedValue([model("small", { recommended: true, downloaded_bytes: 100_000_000 })]);
    renderWizard(runtimeView({ state: "error", model: "small", error: { code: "download_failed", message: "The download was interrupted." } }));
    expect(await screen.findByText("100 MB of 282 MB are already downloaded; the download continues.")).toBeInTheDocument();
    expect(screen.getByText("The download was interrupted.")).toBeInTheDocument();
  });
});
