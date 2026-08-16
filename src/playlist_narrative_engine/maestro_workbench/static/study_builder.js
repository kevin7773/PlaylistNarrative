(function () {
  "use strict";

  const TEMPLATES = Object.freeze({
    exact_count: Object.freeze({
      label: "Exact generated count",
      subject: "RUN",
      interpretation: null,
      selector: ["selector.run", "1"],
      evaluator: ["subject.integer_equals", "1"],
      aggregate: ["aggregate.single_subject", "1"],
      authority: "STRUCTURAL_DERIVATION",
      valueType: "INTEGER",
      derivation: ["structural.placement_count", "1"],
      defaultOutcomeInput: "CONSTRAINT_RESULTS",
    }),
    displayed_explicit: Object.freeze({
      label: "Displayed Explicit designation",
      subject: "PLACEMENT_FIELD",
      field: "explicit_flag",
      interpretation: "FIELD_PREDICATE",
      selector: ["selector.all_placements", "1"],
      evaluator: ["subject.boolean_equals", "1"],
      aggregate: ["aggregate.all_subjects_required", "1"],
      authority: "DIRECT_OBSERVATION",
      valueType: "BOOLEAN",
      defaultOutcomeInput: "STRUCTURED_SUBJECT_RESULTS",
    }),
    lexical_title: Object.freeze({
      label: "Standalone token in displayed title",
      subject: "PLACEMENT_FIELD",
      field: "display_title",
      interpretation: "FIELD_PREDICATE",
      selector: ["selector.all_placements", "1"],
      evaluator: ["subject.lexical_standalone_token", "1"],
      aggregate: ["aggregate.all_subjects_required", "1"],
      authority: "DIRECT_OBSERVATION",
      valueType: "TEXT",
      defaultOutcomeInput: "STRUCTURED_SUBJECT_RESULTS",
    }),
  });

  const ref = ([evaluator_key, evaluator_version]) => ({evaluator_key, evaluator_version});
  const textParameter = (parameter_key, text_value, ordinal = 1) => ({parameter_key, ordinal, value_type: "TEXT", text_value});
  function formatValidationIssue(issue) {
    const path = (issue.location || []).reduce((value, part) => typeof part === "number" ? `${value}[${part}]` : value ? `${value}.${part}` : String(part), "");
    return `${path ? `${path}: ` : ""}${issue.message}`;
  }

  const SHA256_K = Object.freeze([
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
  ]);
  const rotateRight = (value, count) => (value >>> count) | (value << (32 - count));

  // One portable SHA-256 definition is used in every browser context, including
  // non-secure LAN HTTP origins where Web Crypto is intentionally unavailable.
  function sha256(value) {
    const bytes = new TextEncoder().encode(value);
    const bitLength = bytes.length * 8;
    const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
    const padded = new Uint8Array(paddedLength);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000), false);
    view.setUint32(paddedLength - 4, bitLength >>> 0, false);
    const hash = new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
    const words = new Uint32Array(64);
    for (let offset = 0; offset < paddedLength; offset += 64) {
      for (let index = 0; index < 16; index += 1) words[index] = view.getUint32(offset + index * 4, false);
      for (let index = 16; index < 64; index += 1) {
        const x = words[index - 15]; const y = words[index - 2];
        const s0 = rotateRight(x, 7) ^ rotateRight(x, 18) ^ (x >>> 3);
        const s1 = rotateRight(y, 17) ^ rotateRight(y, 19) ^ (y >>> 10);
        words[index] = (words[index - 16] + s0 + words[index - 7] + s1) >>> 0;
      }
      let [a,b,c,d,e,f,g,h] = hash;
      for (let index = 0; index < 64; index += 1) {
        const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choice = (e & f) ^ (~e & g);
        const temp1 = (h + sum1 + choice + SHA256_K[index] + words[index]) >>> 0;
        const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const temp2 = (sum0 + majority) >>> 0;
        h=g; g=f; f=e; e=(d+temp1)>>>0; d=c; c=b; b=a; a=(temp1+temp2)>>>0;
      }
      [a,b,c,d,e,f,g,h].forEach((value,index)=>{hash[index]=(hash[index]+value)>>>0;});
    }
    return [...hash].map(value=>value.toString(16).padStart(8,"0")).join("");
  }

  function constraintPlan(template, config) {
    const measurement = {
      measurement_key: "observed",
      authority: template.authority,
      value_type: template.valueType,
      required: true,
      evidence_required: template.authority !== "STRUCTURAL_DERIVATION",
      unavailable_policy: "MUST_HAVE_VALUE",
    };
    if (template.derivation) {
      measurement.derivation_key = template.derivation[0];
      measurement.derivation_version = template.derivation[1];
    }
    const parameters = [];
    if (config.template === "exact_count") {
      parameters.push({parameter_key: "expected", value_type: "INTEGER", integer_value: Number(config.expectedCount)});
    } else if (config.template === "displayed_explicit") {
      parameters.push({parameter_key: "expected", value_type: "BOOLEAN", boolean_value: Boolean(config.expectedExplicit)});
      parameters.push(
        {parameter_key: "mixed_status", value_type: "TEXT", text_value: "PARTIAL"},
        {parameter_key: "all_fail_status", value_type: "TEXT", text_value: "FAIL"},
        {parameter_key: "unknown_status", value_type: "TEXT", text_value: "UNKNOWN"},
      );
    } else {
      parameters.push({parameter_key: "token", value_type: "TEXT", text_value: config.token});
      parameters.push({parameter_key: "case_sensitive", value_type: "BOOLEAN", boolean_value: false});
      parameters.push(
        {parameter_key: "mixed_status", value_type: "TEXT", text_value: "PARTIAL"},
        {parameter_key: "all_fail_status", value_type: "TEXT", text_value: "FAIL"},
        {parameter_key: "unknown_status", value_type: "TEXT", text_value: "UNKNOWN"},
      );
    }
    return {
      instrumentation_version: "1",
      subject_kind: template.subject,
      subject_field: template.field || null,
      subject_selector: ref(template.selector),
      subject_evaluator: ref(template.evaluator),
      aggregate_evaluator: ref(template.aggregate),
      require_complete_subject_set: true,
      allow_partial_subject_status: false,
      measurement_definitions: [measurement],
      parameters,
      vocabulary_terms: [],
    };
  }

  function constraintDefinition(template, config, blockNumber) {
    const prefix = `b${String(blockNumber).padStart(2, "0")}`;
    let text;
    let evaluation;
    if (config.template === "exact_count") {
      text = `Playlist must contain exactly ${Number(config.expectedCount)} tracks.`;
      evaluation = `Compare the structurally derived placement count with ${Number(config.expectedCount)}.`;
    } else if (config.template === "displayed_explicit") {
      text = `Every displayed track must have Explicit designation ${config.expectedExplicit ? "present" : "absent"}.`;
      evaluation = `Evaluate each governed displayed explicit_flag against ${Boolean(config.expectedExplicit)}.`;
    } else {
      text = `Every displayed track title must contain standalone word ${JSON.stringify(config.token)}.`;
      evaluation = `Evaluate each governed display_title using the registered standalone-token evaluator.`;
    }
    return {
      constraint_key: `${prefix}-${config.template.replaceAll("_", "-")}`,
      constraint_type: config.template,
      constraint_text: text,
      is_hard_constraint: true,
      evaluation_rule: evaluation,
      permitted_result_provenance: "DERIVED_QUERY_RESULT",
      unknown_handling: "UNKNOWN remains UNKNOWN and is governed by the registered outcome policy.",
      structured_evaluation_plan: constraintPlan(template, config),
    };
  }

  function outcomePlan(config, template, constraintKeys) {
    const inputKind = config.outcomeKind === "AUTO" ? template.defaultOutcomeInput : config.outcomeKind;
    const calculatorKey = inputKind === "STRUCTURED_SUBJECT_RESULTS" ? "outcome.subject_status_rate" : "outcome.constraint_status_rate";
    const numerator = config.success === "PASS_PARTIAL" ? ["PASS", "PARTIAL"] : ["PASS"];
    return {
      outcome_key: "registered-compliance-rate",
      calculator_key: calculatorKey,
      calculator_version: "1",
      input_kind: inputKind,
      output_value_type: "DECIMAL",
      constraint_bindings: constraintKeys.map((constraint_key, index) => ({constraint_key, binding_role: "CONTRIBUTOR", ordinal: index + 1})),
      ...(inputKind === "STRUCTURED_SUBJECT_RESULTS" ? {
        subject_interpretation: template.interpretation,
        subject_kinds: [template.subject],
      } : {}),
      parameters: [
        ...numerator.map((status, index) => textParameter("numerator_status", status, index + 1)),
        ...["PASS", "PARTIAL", "FAIL"].map((status, index) => textParameter("denominator_status", status, index + 1)),
        textParameter("unknown_policy", config.unknownPolicy),
        textParameter("missing_input_policy", config.missingInputPolicy),
      ],
      disposition_policies: [
        {population_state: "EXPERIMENT_RECORDED", treatment: "CALCULATE"},
        {population_state: "PENDING", treatment: "MISSING"},
        {population_state: "MAESTRO_REFUSAL_RECORDED", treatment: config.refusalTreatment},
        {population_state: "MAESTRO_FAILURE_RECORDED", treatment: config.failureTreatment},
      ],
    };
  }

  function analysisPlan(config) {
    return {
      analysis_key: "paired-compliance-difference",
      calculator_key: "analysis.paired_difference",
      calculator_version: "1",
      population_scope: "ALL_REGISTERED_PLANNED_RUNS",
      output_shape_key: "PAIRED_DIFFERENCE_SUMMARY",
      output_shape_version: "1",
      dimensions: [
        {dimension_role: "MATCH", dimension_key: "BLOCK", ordinal: 1},
        {dimension_role: "MATCH", dimension_key: "REPLICATE", ordinal: 2},
      ],
      condition_bindings: [
        {comparison_role: "LEFT", condition_key: config.leftKey},
        {comparison_role: "RIGHT", condition_key: config.rightKey},
      ],
      parameters: [
        textParameter("difference_direction", config.direction),
        textParameter("pair_completeness", "REQUIRED"),
        textParameter("missing_policy", "NOT_CALCULABLE"),
      ],
    };
  }

  function prompt(base, framing) {
    return [base.trim(), framing.trim()].filter(Boolean).join("\n\n");
  }

  async function compile(config) {
    const template = TEMPLATES[config.template];
    if (!template) throw new Error("Unsupported structured constraint template.");
    const researchQuestion = (config.researchQuestion || "").trim();
    if (!researchQuestion && !(config.objective || "").trim()) throw new Error("Research question is required.");
    const effectiveSeed = (config.seed || "").trim() || `guided-${(await sha256(`${config.studyKey}\n${config.title}\n${researchQuestion}`)).slice(0, 20)}`;
    const objective = (config.objective || "").trim() || `Prospectively evaluate the research question: ${researchQuestion}`;
    const primaryHypothesis = (config.primaryHypothesis || "").trim() || `The registered outcome differs between ${JSON.stringify(config.leftLabel)} and ${JSON.stringify(config.rightLabel)} in the direction defined by the registered analysis.`;
    const nullHypothesis = (config.nullHypothesis || "").trim() || `The registered outcome does not differ between ${JSON.stringify(config.leftLabel)} and ${JSON.stringify(config.rightLabel)}.`;
    const blockCount = Number(config.blockCount);
    const replicates = Number(config.replicates);
    if (!Number.isInteger(blockCount) || blockCount < 1 || blockCount > 6) throw new Error("Block count must be between 1 and 6.");
    if (!Number.isInteger(replicates) || replicates < 1 || replicates > 20) {
      throw new Error("Replicates must be an integer from 1 through 20.");
    }
    const blocks = Array.from({length: blockCount}, (_, index) => ({
      block_key: `b${String(index + 1).padStart(2, "0")}`,
      label: `Block ${index + 1}`,
      block_definition: `Builder-declared block ${index + 1} using ${template.label}.`,
    }));
    const constraints = blocks.map((_, index) => constraintDefinition(template, config, index + 1));
    const candidates = [];
    for (const [condition_key, framing] of [[config.leftKey, config.leftFraming], [config.rightKey, config.rightFraming]]) {
      for (const [index, block] of blocks.entries()) {
        for (let replicate = 1; replicate <= replicates; replicate += 1) {
          candidates.push({
            run_key: `${block.block_key}-${condition_key}-r${replicate}`,
            condition_key,
            block_key: block.block_key,
            replicate_number: replicate,
            planned_prompt_text: prompt(config.basePrompt, framing),
            planned_source_system: config.sourceSystem || null,
            replacement_for_run_key: null,
            applicable_constraint_keys: [constraints[index].constraint_key],
          });
        }
      }
    }
    const ranked = await Promise.all(candidates.map(async run => ({run, rank: await sha256(`${effectiveSeed}\n${run.run_key}`)})));
    ranked.sort((a, b) => a.rank.localeCompare(b.rank) || a.run.run_key.localeCompare(b.run.run_key));
    const runs = ranked.map(({run}, index) => ({...run, randomized_ordinal: index + 1}));
    const constraintKeys = constraints.map(item => item.constraint_key);
    const outcome = outcomePlan(config, template, constraintKeys);
    return {
      study_key: config.studyKey,
      title: config.title,
      protocol: {
        version_number: 1,
        amendment_reason: null,
        objective,
        primary_hypothesis: primaryHypothesis,
        null_hypothesis: nullHypothesis,
        design_summary: `${researchQuestion ? `Research question: ${researchQuestion} ` : ""}Two-condition calculator-governed Study with ${blockCount} block(s), ${replicates} replicate(s) per condition/block, and the ${template.label} structured template.`,
        planned_sample_size: runs.length,
        randomization_method: "Deterministic SHA-256 ordering of UTF-8 randomization_seed + newline + run_key; lexical digest order.",
        randomization_seed: effectiveSeed,
        operational_failure_policy: config.operationalPolicy,
        operational_failure_consumes_run: false,
        refusal_policy: config.refusalPolicy,
        missing_result_policy: config.missingPolicy,
        conditions: [
          {condition_key: config.leftKey, label: config.leftLabel, role: "CONTROL", exact_factor_definition: config.leftFactor || `${config.leftLabel}: shared base instruction plus the explicitly entered Condition A instruction.`},
          {condition_key: config.rightKey, label: config.rightLabel, role: "TREATMENT", exact_factor_definition: config.rightFactor || `${config.rightLabel}: shared base instruction plus the explicitly entered Condition B instruction.`},
        ],
        blocks,
        constraint_definitions: constraints,
        outcome_definitions: [{
          outcome_key: "registered-compliance-rate", role: "PRIMARY",
          unit_of_analysis: outcome.input_kind === "STRUCTURED_SUBJECT_RESULTS" ? "registered structured subject result" : "registered aggregate ConstraintResult",
          outcome_definition: "Registered success-status rate over the execution-contract-authorized inputs.",
          computation_rule: "Use the registered outcome calculator and its frozen numerator and denominator statuses.",
          missing_data_rule: "Use the registered UNKNOWN and missing-input policies without imputation.",
          refusal_handling: "Use the registered refusal disposition policy.",
          operational_failure_handling: "Non-consuming operational failures remain outside the registered calculator population.",
        }],
        analysis_definitions: [{
          analysis_key: "paired-compliance-difference", outcome_key: "registered-compliance-rate",
          analysis_population: "All registered planned runs paired by block and replicate.",
          comparison_definition: "Compare the explicitly bound LEFT and RIGHT conditions.",
          aggregation_rule: "Use the registered paired-difference calculator only.",
          exclusion_rule: "Required incomplete pairs are NOT_CALCULABLE without imputation.",
          reporting_rule: "Descriptive registered values only; no significance or causal claim.",
        }],
        planned_runs: runs,
        execution_contract: {
          contract_version: "1",
          outcome_calculation_plans: [outcome],
          analysis_calculation_plans: [analysisPlan(config)],
        },
      },
    };
  }

  const api = Object.freeze({templates: TEMPLATES, compile, sha256, formatValidationIssue});
  if (typeof window !== "undefined") window.GuidedStudyBuilder = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
