import { execSync } from "child_process";
import * as readline from "readline";
import * as path from "path";
import * as fs from "fs";

interface StopHookInput {
  session_id: string;
  stop_hook_active?: boolean;
}

interface HookOutput {
  result: "continue" | "block";
  message?: string;
}

const TRACKED_FOLDERS = ["core", "healthsparq", "sapphire"];

async function readStdin(): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin });
  const lines: string[] = [];
  for await (const line of rl) {
    lines.push(line);
  }
  return lines.join("\n");
}

function getModifiedFilesInDir(dir: string): string[] {
  try {
    // Get both staged and unstaged changes
    const gitStatus = execSync("git status --porcelain", {
      encoding: "utf-8",
      cwd: dir,
    });

    // Parse git status output: first 2 chars are status, rest is filename
    const files = gitStatus
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => line.substring(3).trim())
      // Handle renamed files (old -> new)
      .map((file) => (file.includes(" -> ") ? file.split(" -> ")[1] : file));

    return files;
  } catch {
    return [];
  }
}

function getRelevantChanges(): Map<string, string[]> {
  const changesByFolder = new Map<string, string[]>();
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

  for (const folder of TRACKED_FOLDERS) {
    const folderPath = path.join(projectDir, folder);

    // Check if folder exists and is a git repo (submodule)
    if (!fs.existsSync(folderPath)) continue;

    const isSubmodule = fs.existsSync(path.join(folderPath, ".git"));

    let files: string[];
    if (isSubmodule) {
      // Get changes from within the submodule
      files = getModifiedFilesInDir(folderPath);
    } else {
      // Get changes from parent repo, filtered to this folder
      const allFiles = getModifiedFilesInDir(projectDir);
      files = allFiles.filter((f) => f.startsWith(folder + "/"));
    }

    // Group by subfolder
    for (const file of files) {
      // Skip CLAUDE.md files themselves
      if (file.endsWith("CLAUDE.md")) continue;

      // Skip common non-code files
      if (
        file.includes("__pycache__") ||
        file.endsWith(".pyc") ||
        file.includes("egg-info")
      )
        continue;

      // Determine the subfolder path
      const parts = file.split("/");
      let subfolderKey: string;

      if (parts.length >= 2) {
        // e.g., io/base.py -> core/io/
        subfolderKey = `${folder}/${parts[0]}/`;
      } else {
        // Root level file in the folder
        subfolderKey = `${folder}/`;
      }

      const existing = changesByFolder.get(subfolderKey) || [];
      existing.push(`${folder}/${file}`);
      changesByFolder.set(subfolderKey, existing);
    }
  }

  return changesByFolder;
}

async function main(): Promise<void> {
  try {
    const input = await readStdin();
    JSON.parse(input); // Validate input is valid JSON

    // Get modified files from git (including submodules)
    const relevantChanges = getRelevantChanges();

    let output: HookOutput;

    if (relevantChanges.size === 0) {
      // No relevant changes, continue without message
      output = { result: "continue" };
    } else {
      // Build message with folders that need CLAUDE.md updates
      const foldersToUpdate = Array.from(relevantChanges.keys());
      const changesSummary = Array.from(relevantChanges.entries())
        .map(
          ([folder, files]) =>
            `- **${folder}**: ${files.length} file(s) changed`,
        )
        .join("\n");

      const filesList = Array.from(relevantChanges.values()).flat().slice(0, 20).join("\n- ");

      const message = `
## MANDATORY: CLAUDE.md Documentation Update Required

**ACTION REQUIRED:** You MUST spawn a subagent NOW to review and update CLAUDE.md files.

**Files modified:**
- ${filesList}

**Affected folders:**
${foldersToUpdate.map((f) => `- ${f}`).join("\n")}

**EXECUTE THIS IMMEDIATELY - Use the Task tool:**

subagent_type: "general-purpose"
prompt: |
  CONTEXT: You are a WORKER agent updating documentation.

  TASK: Review changes in these folders and update their CLAUDE.md files:
  ${foldersToUpdate.map((f) => `- ${f}`).join("\n  ")}

  FILES CHANGED:
  - ${filesList}

  INSTRUCTIONS:
  1. Read the changed files to understand what was modified
  2. Read the existing CLAUDE.md in each affected folder
  3. Update CLAUDE.md if the changes affect:
     - Public APIs or function signatures
     - Usage patterns or examples
     - Architecture or module responsibilities
     - Key classes, methods, or configuration
  4. Keep updates minimal - only document significant changes
  5. If no significant changes, report "No CLAUDE.md updates needed"

  Report: List each CLAUDE.md file and whether it was updated or skipped.

DO NOT skip this step. Documentation accuracy is critical for agent effectiveness.
`;

      output = {
        result: "continue",
        message: message.trim(),
      };
    }

    console.log(JSON.stringify(output));
  } catch {
    // On error, continue without blocking
    const output: HookOutput = { result: "continue" };
    console.log(JSON.stringify(output));
  }
}

main();
