# Spec Delta

## Purpose

Estimates what a phone model sells for used on OLX.kz from the listings the pipeline has already collected,
and uses that estimate to reward listings priced below the used market and flag ones priced implausibly low.

## ADDED Requirements

### Requirement: Price history across runs
The system SHALL record, for every analyzed listing, its link, recognized model, storage (when stated in the
title), asking price and the time it was seen, in a price history shared by all sessions. A listing seen again
SHALL update its existing entry rather than add a second one.

#### Scenario: Same listing in two runs
- **WHEN** a listing with the same link is analyzed in two runs and its price changed between them
- **THEN** the price history holds one entry for that link, with the latest price and time seen

#### Scenario: Listing without a recognized model
- **WHEN** the model of a listing cannot be recognized from its title
- **THEN** the listing is not recorded in the price history

### Requirement: Median used price per model
The system SHALL compute a model's median used price from price-history entries seen within the last 60 days.
When the listing's storage is known and at least 5 entries share both model and storage, the median SHALL use
those entries; otherwise it SHALL use all entries of the model. With fewer than 5 entries the model SHALL have
no median.

#### Scenario: Enough samples for model and storage
- **WHEN** a listing is "Samsung S23 Ultra 256GB" and the history has 7 entries for S23 Ultra 256GB within 60 days
- **THEN** its median is computed from those 7 entries

#### Scenario: Too few samples for the storage variant
- **WHEN** the history has 3 entries for S23 Ultra 512GB and 12 for S23 Ultra overall
- **THEN** a 512GB listing uses the median of all 12 S23 Ultra entries

#### Scenario: Not enough data
- **WHEN** a model has 4 entries within 60 days
- **THEN** the model has no median and its listings get no median-based factor

#### Scenario: Old entries ignored
- **WHEN** an entry was last seen more than 60 days ago
- **THEN** it does not count toward the median or the sample size

### Requirement: Below-median value factor
The system SHALL add a value factor for a listing priced below its model's median, with points increasing at
10%, 20% and 30% below the median, and SHALL add no points for a listing at or above the median. This factor
SHALL be independent of the launch-price discount: a listing can receive both.

#### Scenario: Listing 25% below median
- **WHEN** a model's median is 200,000 KZT and a listing asks 150,000 KZT
- **THEN** the listing receives the 20%-below-median points and a factor naming the median and sample size

#### Scenario: Listing above median
- **WHEN** a listing asks more than its model's median
- **THEN** it receives no median-based points

#### Scenario: Model missing from the launch-price table
- **WHEN** a model has a median but no launch-price entry
- **THEN** the listing still receives the median-based factor

### Requirement: Implausibly low price warning
The system SHALL flag a listing priced 50% or more below its model's median as suspicious, award it no
median-based points, and show the warning in the report.

#### Scenario: Price far below median
- **WHEN** a model's median is 300,000 KZT and a listing asks 140,000 KZT
- **THEN** the listing gets no median-based points and the report shows a suspicious-price warning

### Requirement: Median shown in the report
The report SHALL show, for each listing that has a median, the median price and the number of listings it was
computed from.

#### Scenario: Report line
- **WHEN** a listing's model median is 180,000 KZT from 14 listings
- **THEN** the report entry shows the median 180,000 KZT and "14 listings"
