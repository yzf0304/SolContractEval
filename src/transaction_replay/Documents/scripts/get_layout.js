const fs = require("fs");
const parser = require("solidity-parser-antlr");
const path = require("path");

// Get variable type as a string
function getTypeString(typeNode) {
  if (!typeNode) return "";
  switch (typeNode.type) {
    case 'ElementaryTypeName':
      return typeNode.name;
    case 'Mapping':
      return `mapping(${getTypeString(typeNode.keyType)} => ${getTypeString(typeNode.valueType)})`;
    case 'ArrayTypeName':
      return typeNode.length ? `${getTypeString(typeNode.baseTypeName)}[${typeNode.length.value}]` : `${getTypeString(typeNode.baseTypeName)}[]`;
    case 'UserDefinedTypeName':
      return typeNode.namePath;
    default:
      return "unknown";
  }
}

// Recursively expand inheritance chain in declared order (preserve order)
function expandInheritance(contractName, contracts, contractInherits, visited = new Set()) {
  if (visited.has(contractName)) return [];

  visited.add(contractName);
  const bases = [];

  for (const base of (contractInherits[contractName] || [])) {
    bases.push(...expandInheritance(base, contracts, contractInherits, visited));
  }

  return [...bases, contracts[contractName]]; // Final subclass at the end
}

// Main function: extract layout
function extractStorageLayout(sourceCode, targetContractName = null) {
  const layout = [];
  let currentSlot = 0;

  const ast = parser.parse(sourceCode, { tolerant: true });

  const contracts = {};
  const contractInherits = {};

  parser.visit(ast, {
    ContractDefinition(node) {
      contracts[node.name] = node;
      contractInherits[node.name] = (node.baseContracts || []).map(b => b.baseName.namePath);
    }
  });

  const targetName = targetContractName || Object.keys(contracts).slice(-1)[0];
  const inheritanceChain = expandInheritance(targetName, contracts, contractInherits);

  for (const contractNode of inheritanceChain) {
    for (const subNode of contractNode.subNodes) {
      if (subNode.type === "StateVariableDeclaration") {
        for (const varDecl of subNode.variables) {
          if (varDecl.isDeclaredConst || varDecl.isImmutable) continue;
          layout.push({
            name: varDecl.name,
            type: getTypeString(varDecl.typeName),
            slot: currentSlot++
          });
        }
      }
    }
  }

  return layout;
}

// Entry point
function main() {
  const contractPath = path.join(__dirname, "..", "contracts", "TargetContract.sol");
  const sourceCode = fs.readFileSync(contractPath, "utf8");

  const layout = extractStorageLayout(sourceCode, "{contract_name}");
  console.log(layout)
  fs.writeFileSync("storageLayout.json", JSON.stringify(layout, null, 2));
}

main();
