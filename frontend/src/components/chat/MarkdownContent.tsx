"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SyntaxHighlighter = require("react-syntax-highlighter").Prism;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { oneDark, oneLight } = require("react-syntax-highlighter/dist/cjs/styles/prism");

interface Props {
  content: string;
}

export function MarkdownContent({ content }: Props) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isDark = mounted ? resolvedTheme === "dark" : false;

  return (
    <div className="prose-chat text-[var(--text-primary)]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { className, children, ...rest } = props;
            const match = /language-(\w+)/.exec(className || "");
            const codeText = String(children).replace(/\n$/, "");
            const isBlock = !!match || codeText.includes("\n");

            if (isBlock) {
              return (
                <SyntaxHighlighter
                  language={match?.[1] ?? "text"}
                  style={isDark ? oneDark : oneLight}
                  customStyle={{
                    margin: 0,
                    borderRadius: "0.625rem",
                    fontSize: "0.8rem",
                    lineHeight: "1.6",
                  }}
                  showLineNumbers={codeText.split("\n").length > 5}
                  wrapLongLines
                >
                  {codeText}
                </SyntaxHighlighter>
              );
            }

            return (
              <code
                className="bg-gray-100 dark:bg-neutral-700 text-brand-600 dark:text-brand-300 px-1.5 py-0.5 rounded text-sm font-mono"
                {...rest}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
