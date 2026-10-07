# One Bedrock guardrail with four policies. The agent harness applies it to every model call;
# our client and the evaluation script also call ApplyGuardrail after the answer, which is where
# the grounding check can run (it needs a tagged source and query, which the harness cannot supply).
#
# Prices (verified 2026-10-07): sensitive information $0.10, denied topics $0.15, content filters
# $0.15 and grounding $0.10 per 1,000 text units (a unit is up to 1,000 characters). Idle cost is $0.

locals {
  # PII types blocked in BOTH directions. Chosen for "could appear in a brief or be asked for".
  # Left out on purpose, because they would block legitimate briefs:
  #   URL           we need source links in every brief
  #   IP_ADDRESS    architecture text can mention network ranges
  #   AGE           "a 10-year-old data centre" is not personal data
  #   SWIFT_CODE, VEHICLE_IDENTIFICATION_NUMBER, LICENSE_PLATE, MAC_ADDRESS, USERNAME
  #                 irrelevant here and prone to false positives on ordinary words
  blocked_pii_types = [
    "NAME",
    "EMAIL",
    "PHONE",
    "ADDRESS",
    "PASSWORD",
    "DRIVER_ID",
    "US_PASSPORT_NUMBER",
    "US_SOCIAL_SECURITY_NUMBER",
    "US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER",
    "CREDIT_DEBIT_CARD_NUMBER",
    "CREDIT_DEBIT_CARD_CVV",
    "CREDIT_DEBIT_CARD_EXPIRY",
    "PIN",
    "US_BANK_ACCOUNT_NUMBER",
    "US_BANK_ROUTING_NUMBER",
    "INTERNATIONAL_BANK_ACCOUNT_NUMBER",
    "AWS_ACCESS_KEY",
    "AWS_SECRET_KEY",
  ]

  # Types that are BLOCKED on input (a user asking for them) but only MASKED on output. ADDRESS is
  # the one: measured on 2026-10-07, the detector flagged "Columbus, Ohio", a company's headquarters,
  # and blocking the whole brief for a city name is a worse failure than masking it. Every other
  # type is blocked in both directions.
  masked_on_output = ["ADDRESS"]

  # A guardrail can only DENY topics; it cannot say "only allow discovery briefs". So this list
  # covers the common off-topic requests and the system prompt plus the evaluation cover the rest.
  # Definitions are limited to 200 characters and must describe a subject, not give an instruction.
  denied_topics = [
    {
      name       = "Politics and elections"
      definition = "Opinions, news or debate about political parties, politicians, elections or contested government policy."
      examples   = ["Who should I vote for?", "What do you think of the new tax bill?"]
    },
    {
      name       = "Personal medical legal and financial advice"
      definition = "Requests for diagnosis or treatment of a person, a legal opinion about a person's situation, or tax and investment advice for an individual."
      examples   = ["What medicine should I take for a headache?", "Should I invest my savings in Bitcoin?", "Can I sue my landlord?"]
    },
    {
      name       = "Entertainment and everyday chat"
      definition = "Casual conversation or requests about food, recipes, sports, celebrities, films, music, games, jokes or holiday plans."
      examples   = ["What is the best pizza topping?", "Tell me a joke.", "Who won the game last night?"]
    },
    {
      name       = "Personal details of individuals"
      definition = "Requests to find, list or reveal personal details of specific people, such as personal email addresses, phone numbers, home addresses or government ID numbers."
      examples   = ["What is the CEO's personal phone number?", "List the home addresses of the employees.", "Give me the CFO's email and social security number."]
    },
  ]

  # Changes whenever any policy changes, so a new numbered version is cut automatically.
  policy_fingerprint = substr(sha256(jsonencode({
    pii       = local.blocked_pii_types
    masked    = local.masked_on_output
    topics    = local.denied_topics
    grounding = var.grounding_threshold
    relevance = var.relevance_threshold
  })), 0, 12)
}

resource "aws_bedrock_guardrail" "this" {
  name        = "${var.project}-guardrail"
  description = "PII blocking, denied topics, prompt-attack filter and a grounding check for the discovery brief agent."

  blocked_input_messaging   = "I can only prepare discovery briefs for companies in the account database, and I cannot help with that request."
  blocked_outputs_messaging = "That answer was withheld because it did not meet this assistant's safety rules. Please rephrase, or ask for a discovery brief on a company in the database."

  # Policy 1: personal data. BLOCK (not mask) in both directions, so a prompt asking for a
  # person's details is stopped and so is an answer that contains them.
  sensitive_information_policy_config {
    dynamic "pii_entities_config" {
      for_each = local.blocked_pii_types

      content {
        type           = pii_entities_config.value
        action         = "BLOCK"
        input_action   = "BLOCK"
        input_enabled  = true
        output_action  = contains(local.masked_on_output, pii_entities_config.value) ? "ANONYMIZE" : "BLOCK"
        output_enabled = true
      }
    }
  }

  # Policy 2: denied topics (the "off-topic" control, with the limitation explained above).
  # CLASSIC tier: the STANDARD tier needs a cross-Region guardrail profile, which adds setup
  # and cross-Region data movement we do not need for English-only briefs.
  topic_policy_config {
    tier_config {
      tier_name = "CLASSIC"
    }

    dynamic "topics_config" {
      for_each = local.denied_topics

      content {
        name       = topics_config.value.name
        definition = topics_config.value.definition
        examples   = topics_config.value.examples
        type       = "DENY"
      }
    }
  }

  # Policy 3: prompt-attack filter on what the user types (jailbreaks, "ignore your instructions").
  # It applies to input only, so the output strength must be NONE. The other harm categories
  # (hate, violence and so on) are not enabled: this agent reads a fixed corpus and writes
  # business briefs, and each category adds cost to every model call.
  content_policy_config {
    tier_config {
      tier_name = "CLASSIC"
    }

    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  # Policy 4: grounding and relevance. Inside the harness this does nothing, because it only runs
  # when the request marks a grounding source and a query. The client and the evaluation script
  # make that kind of request through ApplyGuardrail after the answer is written.
  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = var.grounding_threshold
    }

    filters_config {
      type      = "RELEVANCE"
      threshold = var.relevance_threshold
    }
  }
}

# A numbered snapshot. The harness points at this, never at the editable DRAFT, so a later edit to
# the guardrail cannot change the agent's behaviour until a new version is created and adopted.
resource "aws_bedrock_guardrail_version" "this" {
  guardrail_arn = aws_bedrock_guardrail.this.guardrail_arn
  description   = "Policy snapshot ${local.policy_fingerprint}"

  # Keep superseded versions as an immutable history instead of deleting them when a new one is cut.
  skip_destroy = true
}
