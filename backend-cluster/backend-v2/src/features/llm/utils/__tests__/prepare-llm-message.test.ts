import { prepareLlmMessage } from "../prepare-llm-message";

const url = "https://storage.invalid/source";
const prompts = {
  system: (format: string) => `System ${format}`,
  text: (format: string, text: string) => `Text ${format}: ${text}`,
  image: () => "Analyze image",
  file: (format: string) => `Analyze ${format}`,
};

afterEach(() => jest.restoreAllMocks());

it("returns exactly the downloaded text used in the model message without another fetch", async () => {
  const source =
    '\uFEFFDate;Memo;Amount\r\n2026-10-01;"Café\nFrühstück";-23,10\r\n';
  const fetchFile = jest
    .spyOn(global, "fetch")
    .mockResolvedValue(new Response(source));
  const prepared = await prepareLlmMessage({
    fileUrl: url,
    format: "csv",
    mediaType: "text/csv",
    prompts,
  });
  // Response.text performs the platform's UTF-8 BOM removal once; grounding and
  // the model must receive the same decoded string, including its line endings.
  const decoded = source.slice(1);
  expect(prepared).toEqual({
    system: "System csv",
    sourceText: decoded,
    messages: [{ role: "user", content: `Text csv: ${decoded}` }],
  });
  expect(fetchFile).toHaveBeenCalledTimes(1);
  expect(fetchFile).toHaveBeenCalledWith(url);
});

it.each([
  {
    format: "png",
    mediaType: "image/png",
    part: { type: "image", image: url },
    prompt: "Analyze image",
  },
  {
    format: "pdf",
    mediaType: "application/pdf",
    part: { type: "file", mediaType: "application/pdf", data: url },
    prompt: "Analyze pdf",
  },
])(
  "does not invent sourceText or download binary $format payloads",
  async ({ format, mediaType, part, prompt }) => {
    const fetchFile = jest.spyOn(global, "fetch");
    const prepared = await prepareLlmMessage({
      fileUrl: url,
      format,
      mediaType,
      prompts,
    });
    expect(prepared).toEqual({
      system: `System ${format}`,
      messages: [
        { role: "user", content: [part, { type: "text", text: prompt }] },
      ],
    });
    expect(prepared).not.toHaveProperty("sourceText");
    expect(fetchFile).not.toHaveBeenCalled();
  },
);
