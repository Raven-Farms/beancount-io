import fs from "fs";
import path from "path";
import {
  deleteEmptiesFolder,
  isFolderGone,
  popPathStack,
  popPathStackFrom,
} from "../utils";

/**
 * w21/088: git keeps no empty folders, so deleting a folder's last file removes
 * it, and since w23/014 its listing answers NOT_FOUND. The browser refetched
 * that folder and stuck on "Failed to load", which pull to refresh could not
 * clear.
 */
const notFound = { graphQLErrors: [{ extensions: { code: "NOT_FOUND" } }] };
const offline = { graphQLErrors: [], networkError: new Error("offline") };

describe("a folder that no longer exists", () => {
  const stack = ["", "qa-20261020"];

  it("is a NOT_FOUND below the root, and steps up to the parent", () => {
    expect(isFolderGone(notFound, stack)).toBe(true);
    expect(popPathStack(stack)).toEqual([""]);
  });

  it("is not an offline listing, nor a NOT_FOUND at the root", () => {
    expect(isFolderGone(offline, stack)).toBe(false);
    expect(isFolderGone(notFound, [""])).toBe(false);
  });

  it("is left by deleting its only file, not one of two", () => {
    expect(deleteEmptiesFolder(stack, 1)).toBe(true);
    expect(deleteEmptiesFolder(stack, 2)).toBe(false);
    // The root lists even when empty.
    expect(deleteEmptiesFolder([""], 1)).toBe(false);
  });

  it("is what the browser steps up from", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "index.tsx"),
      "utf8",
    );
    expect(
      source.includes("if (deleteEmptiesFolder(pathStack, sorted.length)) {"),
    ).toBe(true);
    expect(
      source.includes("const folderGone = isFolderGone(error, pathStack);"),
    ).toBe(true);
  });
});

// w21/448: Back tapped while the delete ran moved the browser up already, and
// the delete then stepped up from where it had got to.
describe("stepping up after the delete finishes", () => {
  it("steps up from the folder it emptied", () => {
    expect(popPathStackFrom(["", "a", "a/b"], "a/b")).toEqual(["", "a"]);
  });

  it("stays where the user went meanwhile", () => {
    // Tapped in a/b, went up to a while it ran.
    expect(popPathStackFrom(["", "a"], "a/b")).toEqual(["", "a"]);
    expect(popPathStackFrom([""], "a/b")).toEqual([""]);
  });

  it("is wired with the folder the delete was tapped in", () => {
    const source = fs
      .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "updatePathStack((stack)=>popPathStackFrom(stack,tappedIn))",
      ),
    ).toBe(true);
    expect(
      source.includes("consttappedIn=pathStack[pathStack.length-1]!"),
    ).toBe(true);
  });
});
