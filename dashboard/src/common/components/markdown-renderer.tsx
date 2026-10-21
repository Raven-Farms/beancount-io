import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { CodeBlock } from "@/common/components/code-block";
import { ExternalLink } from "lucide-react";
import type { Components } from "react-markdown";
import { useMemo, type ComponentProps, type ReactNode } from "react";
import { LedgerImage } from "@/common/components/ledger-image";
import { getLedgerFileBlobPath } from "@/common/hooks/use-file-navigate";
import { resolveReadmeReference } from "@/common/lib/readme-reference";

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /** Nest a document under its containing page's heading, without editing it. */
  headingOffset?: number;
  /**
   * The ledger file this Markdown was read from. Its relative links then open
   * the files they name and its relative images show those files' bytes,
   * resolved from its folder (w4/m37). Other Markdown keeps authored URLs.
   */
  source?: { ledgerId: string; path: string };
}

const headingTags = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;

interface HastNode {
  type: string;
  tagName?: string;
  value?: string;
  properties?: { className?: unknown };
  children?: HastNode[];
}

function hastText(node: HastNode): string {
  if (node.type === "text") return node.value ?? "";
  return (node.children ?? []).map(hastText).join("");
}

const components: Components = {
  // A block is the parsed <pre>, whatever its language: an unlabelled fence
  // or an indented block has no `language-` class, and treating that as
  // inline collapsed the author's lines (w4/269). The `code` override below
  // therefore only ever sees inline spans.
  pre({ children, node }) {
    const code = (node as HastNode | undefined)?.children?.find(
      (child) => child.type === "element" && child.tagName === "code",
    );
    if (!code) return <pre>{children}</pre>;
    const classes = code.properties?.className;
    const languageClass = (Array.isArray(classes) ? classes : [])
      .map(String)
      .find((name) => name.startsWith("language-"));
    return (
      <CodeBlock
        code={hastText(code).replace(/\n$/, "")}
        language={languageClass?.slice("language-".length)}
        inline={false}
      />
    );
  },

  code({ children }) {
    return <CodeBlock code={String(children)} inline />;
  },

  a({ children, href, ...props }) {
    const isExternal = href?.startsWith("http");
    return (
      <a
        href={href}
        target={isExternal ? "_blank" : undefined}
        rel={isExternal ? "noopener noreferrer" : undefined}
        className="underline hover:opacity-80 inline-flex items-center gap-1 font-medium"
        {...props}
      >
        {children}
        {isExternal && <ExternalLink className="h-3 w-3" />}
      </a>
    );
  },

  table({ children, ...props }) {
    return (
      <div className="overflow-x-auto my-4 max-w-full">
        <table className="min-w-full border-collapse" {...props}>
          {children}
        </table>
      </div>
    );
  },

  th({ children, ...props }) {
    return (
      <th
        className="border border-border px-4 py-2 bg-muted font-semibold text-left"
        {...props}
      >
        {children}
      </th>
    );
  },

  td({ children, ...props }) {
    return (
      <td className="border border-border px-4 py-2 text-left" {...props}>
        {children}
      </td>
    );
  },

  blockquote({ children, ...props }) {
    return (
      <blockquote
        className="border-l-4 border-current/20 pl-4 my-4 italic opacity-80"
        {...props}
      >
        {children}
      </blockquote>
    );
  },

  ul({ children, ...props }) {
    return (
      <ul className="list-disc ml-6 my-3 space-y-1" {...props}>
        {children}
      </ul>
    );
  },

  ol({ children, ...props }) {
    return (
      <ol className="list-decimal ml-6 my-3 space-y-1" {...props}>
        {children}
      </ol>
    );
  },

  h1({ children, ...props }) {
    return (
      <h1 className="text-2xl font-semibold mt-6 mb-3" {...props}>
        {children}
      </h1>
    );
  },

  h2({ children, ...props }) {
    return (
      <h2 className="text-xl font-semibold mt-6 mb-3" {...props}>
        {children}
      </h2>
    );
  },

  h3({ children, ...props }) {
    return (
      <h3 className="text-lg font-semibold mt-6 mb-3" {...props}>
        {children}
      </h3>
    );
  },

  p({ children, ...props }) {
    return (
      <p className="my-3 leading-relaxed" {...props}>
        {children}
      </p>
    );
  },
};

function sourceComponents({
  ledgerId,
  path,
}: NonNullable<MarkdownRendererProps["source"]>): Components {
  const Anchor = components.a as (props: ComponentProps<"a">) => ReactNode;
  return {
    a({ href, ...props }) {
      delete props.node;
      const target = resolveReadmeReference(href, path);
      return (
        <Anchor
          {...props}
          href={
            target
              ? getLedgerFileBlobPath(ledgerId, target.path, target.suffix)
              : href
          }
        />
      );
    },
    img({ src, alt, title, ...props }) {
      delete props.node;
      const target =
        typeof src === "string" ? resolveReadmeReference(src, path) : null;
      if (!target) return <img src={src} alt={alt} title={title} {...props} />;
      return (
        <LedgerImage
          ledgerId={ledgerId}
          path={target.path}
          alt={alt}
          title={title}
        />
      );
    },
  };
}

export function MarkdownRenderer({
  content,
  className,
  headingOffset = 0,
  source,
}: MarkdownRendererProps) {
  const sourceLedgerId = source?.ledgerId;
  const sourcePath = source?.path;
  const renderedComponents = useMemo<Components>(() => {
    const base =
      sourceLedgerId !== undefined && sourcePath !== undefined
        ? {
            ...components,
            ...sourceComponents({ ledgerId: sourceLedgerId, path: sourcePath }),
          }
        : components;
    if (!headingOffset) return base;
    return {
      ...base,
      ...Object.fromEntries(
        headingTags.map((tag, index) => {
          const Heading =
            headingTags[Math.min(5, Math.max(0, index + headingOffset))];
          return [
            tag,
            function NestedHeading({
              children,
              ...headingProps
            }: ComponentProps<"h1"> & { node?: unknown }) {
              delete headingProps.node;
              return (
                <Heading className="font-semibold mt-6 mb-3" {...headingProps}>
                  {children}
                </Heading>
              );
            },
          ];
        }),
      ),
    };
  }, [headingOffset, sourceLedgerId, sourcePath]);
  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-full overflow-x-auto break-words ${className ?? ""}`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        rehypePlugins={[rehypeRaw, rehypeSanitize]}
        components={renderedComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
