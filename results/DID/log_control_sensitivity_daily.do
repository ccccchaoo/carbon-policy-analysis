*******************************************************
* Robustness: log transformation of skewed controls
* Daily CEADs data; outcome-based association model
*
* Purpose:
*   Address sensitivity to the functional form of controls.
*   Baseline controls are compared with a specification in which
*   the two scale variables most likely to be right-skewed are logged:
*       ln(GDP) and ln(Population Density).
*
*   Ratio/share controls remain in levels:
*       Industrial Structure
*       Urbanization Level
*       Technological Progress (= R&D expenditure / GDP)
*       Fiscal Self-sufficiency (= revenue / expenditure)
*
* Important:
*   - Same TWFE specification as the main analysis
*   - Province-clustered standard errors
*   - Same pre-policy High/Low grouping definitions
*   - Baseline and log-control specifications use the same log-support sample
*     so changes reflect functional form rather than sample composition.
*
* Output:
*   robustness_log_controls_daily.xlsx
*     Sheet 1: Baseline controls
*     Sheet 2: Log controls
*     Sheet 3: Transformations
*******************************************************

clear all
set more off

cd "D:\桌面\sim-degree3.0\results\DID"
sysdir set PLUS "D:\Stata17\ado\plus"

* If needed:
* ssc install reghdfe, replace
* ssc install ftools, replace

*******************************************************
* 0. Load data and define analysis sample
*******************************************************
import excel "日度_ceads.xlsx", firstrow clear

* Keep provinces that issued a corresponding local policy
keep if treated != 0 & !missing(treated)

gen double policy_group = policy_day
drop if missing(policy_group)

gen byte post = (day >= policy_group)

*******************************************************
* 1. Outcomes
*******************************************************
gen double y_total       = Total碳排值
gen double y_aviation    = Aviation碳排值
gen double y_transport   = GroundTransport碳排值
gen double y_industry    = Industry碳排值
gen double y_power       = Power碳排值
gen double y_residential = Residential碳排值

*******************************************************
* 2. Pre-policy grouping variables
*    Keep exactly the same definition as the main analysis:
*    average over the 30 days before local policy issuance.
*******************************************************
gen byte __pre30 = (day >= policy_group - 30 & day < policy_group)

capture confirm variable 碳排强度
if _rc == 0 {
    gen double __carbon_intensity = 碳排强度
}
else {
    gen double __carbon_intensity = Total碳排值 / 生产总值 ///
        if !missing(Total碳排值, 生产总值) & 生产总值 > 0
}

bysort id: egen double group_base_ci = ///
    mean(cond(__pre30 == 1, __carbon_intensity, .))

gen double __power_share = Power碳排值 / Total碳排值 ///
    if !missing(Power碳排值, Total碳排值) & Total碳排值 > 0
bysort id: egen double group_base_power_share = ///
    mean(cond(__pre30 == 1, __power_share, .))

bysort id: egen double group_base_industry2 = ///
    mean(cond(__pre30 == 1, 工业结构, .))

* Province-level medians: each province contributes once
egen byte __idtag = tag(id)

quietly summarize group_base_ci if __idtag == 1 & !missing(group_base_ci), detail
scalar med_ci = r(p50)

quietly summarize group_base_power_share if __idtag == 1 & !missing(group_base_power_share), detail
scalar med_power = r(p50)

quietly summarize group_base_industry2 if __idtag == 1 & !missing(group_base_industry2), detail
scalar med_industry = r(p50)

gen byte high_ci = (group_base_ci > scalar(med_ci)) if !missing(group_base_ci)
gen byte low_ci  = (group_base_ci <= scalar(med_ci)) if !missing(group_base_ci)

gen byte high_power = (group_base_power_share > scalar(med_power)) ///
    if !missing(group_base_power_share)
gen byte low_power = (group_base_power_share <= scalar(med_power)) ///
    if !missing(group_base_power_share)

gen byte high_industry = (group_base_industry2 > scalar(med_industry)) ///
    if !missing(group_base_industry2)
gen byte low_industry = (group_base_industry2 <= scalar(med_industry)) ///
    if !missing(group_base_industry2)

*******************************************************
* 3. Functional-form sensitivity of controls
*******************************************************

* Diagnostics: log requires strictly positive values
quietly count if !missing(生产总值) & 生产总值 <= 0
local nonpos_gdp = r(N)

quietly count if !missing(人口密度) & 人口密度 <= 0
local nonpos_popden = r(N)

* Natural-log transformations of the two scale variables
gen double ln_gdp = ln(生产总值) if 生产总值 > 0
gen double ln_popdensity = ln(人口密度) if 人口密度 > 0

label variable ln_gdp "ln(Regional GDP)"
label variable ln_popdensity "ln(Population Density)"

* Common support for a clean baseline-vs-log comparison
gen byte log_support = !missing(ln_gdp, ln_popdensity)

* Baseline control vector
local controls_base ///
    "工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值"

* Log-control robustness vector:
* Shares/ratios remain in levels; scale variables are logged.
local controls_log ///
    "工业结构 城市化水平 ln_popdensity 技术进步 财政自给率 ln_gdp"

*******************************************************
* 4. Dimensions used in the output table
*******************************************************
local measures "SA_att AS_att SA_outweight AS_outweight"
local specs "baseline log"
local outfile "robustness_log_controls_daily.xlsx"

*******************************************************
* 5. Estimate and write two identically structured sheets
*******************************************************

local firstsheet = 1

foreach spec of local specs {

    if "`spec'" == "baseline" {
        local sheetname "Baseline controls"
        local controls "`controls_base'"
    }
    else {
        local sheetname "Log controls"
        local controls "`controls_log'"
    }

    * Initialize workbook/sheet
    if `firstsheet' == 1 {
        putexcel set "`outfile'", replace sheet("`sheetname'")
        local firstsheet = 0
    }
    else {
        putexcel set "`outfile'", modify sheet("`sheetname'")
    }

    * --------------------------------------------------------
    * Headers: same layout as the main results table
    * --------------------------------------------------------
    putexcel A1=("") B1=("Full") C1=("Carbon Intensity") ///
        E1=("Power Emission Share") G1=("Secondary-Industry Share")
    putexcel C1:D1, merge
    putexcel E1:F1, merge
    putexcel G1:H1, merge

    putexcel A2=("") B2=("(1) Full") ///
        C2=("(2a) Above-median") D2=("(2b) Below-median") ///
        E2=("(3a) Above-median") F2=("(3b) Below-median") ///
        G2=("(4a) Above-median") H2=("(4b) Below-median")

    putexcel A1:H2, bold hcenter

    * --------------------------------------------------------
    * Four panels × six outcomes × seven sample specifications
    * --------------------------------------------------------
    forvalues mnum = 1/4 {

        local m : word `mnum' of `measures'

        if `mnum' == 1 local paneltitle "Panel 1: S-to-A Rel.Att"
        if `mnum' == 2 local paneltitle "Panel 2: A-to-S Rel.Att"
        if `mnum' == 3 local paneltitle "Panel 3: S-to-A OutWeight"
        if `mnum' == 4 local paneltitle "Panel 4: A-to-S OutWeight"

        * Panel starts at rows 3, 11, 19, 27
        local panelrow = 3 + (`mnum' - 1)*8
        putexcel A`panelrow'=("`paneltitle'")
        putexcel A`panelrow':H`panelrow', bold

        * Interaction for this text measure
        capture drop did_current
        gen double did_current = `m' * post

        * Store N from Total regression for each sample column
        forvalues j = 1/7 {
            local N`j' = .
        }

        * Six outcomes
        forvalues onum = 1/6 {

            if `onum' == 1 {
                local yvar y_total
                local ylabel "Total"
            }
            else if `onum' == 2 {
                local yvar y_aviation
                local ylabel "Aviation"
            }
            else if `onum' == 3 {
                local yvar y_transport
                local ylabel "Ground Transport"
            }
            else if `onum' == 4 {
                local yvar y_industry
                local ylabel "Industry"
            }
            else if `onum' == 5 {
                local yvar y_power
                local ylabel "Power"
            }
            else if `onum' == 6 {
                local yvar y_residential
                local ylabel "Residential"
            }

            local outrow = `panelrow' + `onum'
            putexcel A`outrow'=("`ylabel'")

            * Seven sample columns
            forvalues j = 1/7 {

                if `j' == 1 {
                    local col "B"
                    local samplecond "log_support == 1"
                }
                else if `j' == 2 {
                    local col "C"
                    local samplecond "log_support == 1 & high_ci == 1"
                }
                else if `j' == 3 {
                    local col "D"
                    local samplecond "log_support == 1 & low_ci == 1"
                }
                else if `j' == 4 {
                    local col "E"
                    local samplecond "log_support == 1 & high_power == 1"
                }
                else if `j' == 5 {
                    local col "F"
                    local samplecond "log_support == 1 & low_power == 1"
                }
                else if `j' == 6 {
                    local col "G"
                    local samplecond "log_support == 1 & high_industry == 1"
                }
                else if `j' == 7 {
                    local col "H"
                    local samplecond "log_support == 1 & low_industry == 1"
                }

                capture quietly reghdfe `yvar' did_current post `controls' ///
                    if `samplecond', absorb(id day) vce(cluster id)

                if _rc == 0 {
                    local b = _b[did_current]
                    local se = _se[did_current]
                    local t = abs(`b'/`se')

                    * 与此前主结果完全一致的显著性标记方式
                    local star ""
                    if `t' > 2.58 local star "***"
                    else if `t' > 1.96 local star "**"
                    else if `t' > 1.65 local star "*"

                    local bstr : display %9.3f `b'
                    local bstr = strtrim("`bstr'")
                    local display_value "`bstr'`star'"

                    local cell "`col'`outrow'"
                    putexcel `cell'=("`display_value'")

                    * Total-regression sample size shown at bottom of each panel
                    if `onum' == 1 {
                        local N`j' = e(N)
                    }
                }
                else {
                    local cell "`col'`outrow'"
                    putexcel `cell'=("")
                }
            }
        }

        * Sample size row
        local nrow = `panelrow' + 7
        putexcel A`nrow'=("sample size")
        forvalues j = 1/7 {
            if `j' == 1 local col "B"
            if `j' == 2 local col "C"
            if `j' == 3 local col "D"
            if `j' == 4 local col "E"
            if `j' == 5 local col "F"
            if `j' == 6 local col "G"
            if `j' == 7 local col "H"

            local cell "`col'`nrow'"
            putexcel `cell'=(`N`j'')
        }
    }

    * --------------------------------------------------------
    * Formatting
    * --------------------------------------------------------
    putexcel A1:H34, font("Arial",10)
    putexcel A1:H34, hcenter
    putexcel A1:A34, left
    putexcel A3:H3, bold
    putexcel A11:H11, bold
    putexcel A19:H19, bold
    putexcel A27:H27, bold
    putexcel A34:H34, border(bottom, thin)

    * Notes beneath the table
    putexcel A36=("Notes:")
    putexcel B36=("All specifications include province FE, day FE, post, and province-clustered SE.")
    putexcel B37=("Baseline and log-control sheets use the same log-support sample.")

    if "`spec'" == "baseline" {
        putexcel B38=("Controls are entered in their original units.")
    }
    else {
        putexcel B38=("Regional GDP and population density enter in natural logs; ratio/share controls remain in levels.")
    }
}

*******************************************************
* 6. Transformation notes / reviewer-facing diagnostics
*******************************************************
putexcel set "`outfile'", modify sheet("Transformations")

putexcel A1=("Variable") B1=("Baseline") C1=("Log-control robustness") D1=("Reason")
putexcel A1:D1, bold hcenter

putexcel A2=("Regional GDP") ///
    B2=("Level") C2=("ln(GDP)") ///
    D2=("Scale variable; natural log reduces right-skewness")

putexcel A3=("Population Density") ///
    B3=("Level") C3=("ln(Population Density)") ///
    D3=("Scale variable; natural log reduces right-skewness")

putexcel A4=("Industrial Structure") ///
    B4=("Level") C4=("Level") ///
    D4=("Share of secondary-industry value added in GDP")

putexcel A5=("Urbanization Level") ///
    B5=("Level") C5=("Level") ///
    D5=("Share variable")

putexcel A6=("Technological Progress") ///
    B6=("Level") C6=("Level") ///
    D6=("R&D expenditure / GDP ratio, not raw R&D expenditure")

putexcel A7=("Fiscal Self-sufficiency") ///
    B7=("Level") C7=("Level") ///
    D7=("General budget revenue / expenditure ratio")

putexcel A9=("Non-positive GDP observations") B9=(`nonpos_gdp')
putexcel A10=("Non-positive population-density observations") B10=(`nonpos_popden')
putexcel A12=("Interpretation") ///
    B12=("This exercise changes only the functional form of skewed scale controls; the core intensity x post specification, fixed effects, grouping rules, and clustering remain unchanged.")

putexcel A1:D12, font("Arial",10)
putexcel A1:D12, left

*******************************************************
* 7. Finish
*******************************************************
display as result "Robustness workbook created: `outfile'"
display as text "Non-positive GDP observations: `nonpos_gdp'"
display as text "Non-positive population-density observations: `nonpos_popden'"

*******************************************************
* Suggested interpretation:
*
* If coefficient signs/magnitudes and the main Total/Power patterns remain
* similar between the two sheets, the conclusions are insensitive to the
* functional-form treatment of the skewed scale controls.
*
* This robustness does NOT change the interpretation of beta into a causal
* effect; beta remains a conditional association.
*******************************************************
