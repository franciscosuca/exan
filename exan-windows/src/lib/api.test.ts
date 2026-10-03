import { afterEach, describe, expect, it, vi } from "vitest";
import { Api, ApiError } from "./api";

const connection = { baseUrl: "http://127.0.0.1:9999/api", token: "secret-token-123456" };

afterEach(() => vi.unstubAllGlobals());

describe("Api", () => {
  it("sends the bearer secret and JSON bodies", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ session: { version: 1 } }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await new Api(connection).keyFromText("1. B", "replace");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://127.0.0.1:9999/api/key/text");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer " + connection.token);
    expect(JSON.parse(String(init.body))).toEqual({ text: "1. B", mode: "replace" });
  });

  it("turns engine errors into ApiError with code and message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "No answers were found.", code: "nothing_found" }), { status: 422 })));
    const error = await new Api(connection).keyFromText("x", "replace").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 422, code: "nothing_found", message: "No answers were found." });
  });

  it("reports an unreachable engine", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    await expect(new Api(connection).health()).rejects.toMatchObject({ code: "engine_unreachable" });
  });

  it("uploads files as multipart with the grouping field", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ session: { version: 2 }, errors: [] })));
    vi.stubGlobal("fetch", fetchMock);
    await new Api(connection).addParticipants([new File(["x"], "a.jpg", { type: "image/jpeg" })], "page");
    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    const form = init.body as FormData;
    expect(form.get("grouping")).toBe("page");
    expect((form.get("files") as File).name).toBe("a.jpg");
  });
});
