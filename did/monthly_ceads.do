cd "D:\GitHub\carbon-policy-analysis\did"
sysdir set PLUS "D:\Stata17\ado\plus"
* Please select the local Stata environment

*ssc install reghdfe
*ssc install ftools
*ssc install coefplot, replace
*ssc install e
import excel "monthly_ceads.xlsx", firstrow clear

* Process policy_time variable
gen policy_group = policy_month
replace policy_group = 0 if missing(policy_group)

* Generate treatment variable
gen post = (month >= policy_group & !missing(policy_group))
replace post = 0 if missing(policy_group)

* Quantile indicators: degree/out_weight_avg/pagerank/
gen group = degree

* Generate DID interaction term: shock/degree/out_weight_avg/pagerank
gen intensity = degree
gen did = intensity * post



* Define dependent variables 
gen y1 = Aviation
gen y2 = GroundTransport
gen y3 = Industry
gen y4 = Power
gen y5 = Residential
gen y = Total

* Quantiles
sum group, detail
gen intensity_high1 = (group <= r(p100) & group > r(p75)) if !missing(group)
gen intensity_high2 = (group <= r(p75) & group > r(p50)) if !missing(group)
gen intensity_high3 = (group <= r(p50) & group > r(p25)) if !missing(group)
gen intensity_high4 = (group <= r(p25)) if !missing(group)
gen intensity_high5 = (group > r(p50)) if !missing(group)
gen intensity_high6 = (group <= r(p50)) if !missing(group)

* Create result storage matrix (now 6 dependent variables, including Total and 5 subcomponents)
matrix results = J(7, 7, .)  // 7 rows: 6 dependent variables + 1 row for sample size
matrix rownames results = "Total" "Aviation" "Ground Transport" "Industry" "Power" "Residential" "sample size"
matrix colnames results = "full sample" "quantile100-75" "quantile75-50" "quantile50-25" "quantile25-0" "quantile100-50" "quantile50-0"

* Create standard error storage matrix
matrix se_results = J(6, 7, .)  // 6 rows: 6 dependent variables
matrix rownames se_results = "Total" "Aviation" "Ground Transport" "Industry" "Power" "Residential"
matrix colnames se_results = "full sample" "quantile100-75" "quantile75-50" "quantile50-25" "quantile25-0" "quantile100-50" "quantile50-0"

* Create sample size storage matrix
matrix N_results = J(7, 1, .)  // Store sample size for each quantile group
matrix rownames N_results = "full sample" "quantile100-75" "quantile75-50" "quantile50-25" "quantile25-0" "quantile100-50" "quantile50-0"

* Calculate sample sizes for each quantile group
quietly count if !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[1, 1] = r(N)

quietly count if intensity_high1 == 1 & !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[2, 1] = r(N)

quietly count if intensity_high2 == 1 & !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[3, 1] = r(N)

quietly count if intensity_high3 == 1 & !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[4, 1] = r(N)

quietly count if intensity_high4 == 1 & !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[5, 1] = r(N)

quietly count if intensity_high5 == 1 & !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[6, 1] = r(N)

quietly count if intensity_high6 == 1 & !missing(y, did,  GRP, industryStructure, urbanLevel, populationDestiny, techRate, fiscalRate)
matrix N_results[7, 1] = r(N)

* Loop over all regressions and store results (now 6 dependent variables: i=0 to 5)
forval i = 0/5 {
    local row = `i' + 1
    
    forval j = 1/7 {
        if `j' == 1 {
            // Full sample regression
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 2 {
            // Quantile 100-75
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high1 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high1 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 3 {
            // Quantile 75-50
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high2 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high2 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 4 {
            // Quantile 50-25
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high3 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high3 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 5 {
            // Quantile 25-0
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high4 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high4 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 6 {
            // Quantile 100-50
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high5 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high5 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 7 {
            // Quantile 100-50
            if `i' == 0 {
                capture reghdfe y did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high6 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did GRP industryStructure urbanLevel populationDestiny techRate fiscalRate if intensity_high6 == 1, absorb(id month) vce(cluster id)
            }
        }
        
        // Store coefficients and standard errors
        if _rc == 0 {
            matrix results[`row', `j'] = _b[did]
            // Note: se_results matrix has only 6 rows, excluding sample size row
            if `i' < 6 {
                matrix se_results[`row', `j'] = _se[did]
            }
        }
        else {
            matrix results[`row', `j'] = .
            if `i' < 6 {
                matrix se_results[`row', `j'] = .
            }
        }
    }
}


forval j = 1/7 {
    matrix results[7, `j'] = N_results[`j', 1]
}


matrix list results

* Create output table
preserve
clear
set obs 7

* Create variable names
gen sector = ""
forval i = 1/7 {
    local name : word `i' of "Total" "Aviation" "Ground Transport" "Industry" "Power" "Residential" "sample size"
    replace sector = "`name'" in `i'
}

* Add coefficient display (with stars)
gen full_sample = ""
gen quantile100_75 = ""
gen quantile75_50 = ""
gen quantile50_25 = ""
gen quantile25_0 = ""
gen quantile100_50 = ""
gen quantile50_0 = ""

forval i = 1/7 {
    forval j = 1/7 {
        local coef = results[`i', `j']
        
        if `coef' != . {

            if `i' == 7 {
                local display_value = string(`coef', "%9.0f")
            }

            else {
                local se = se_results[`i', `j']
                if `se' != . {
                    local t = abs(`coef'/`se')
                    local star = ""
                    if `t' > 2.58 local star = "***"
                    else if `t' > 1.96 local star = "**" 
                    else if `t' > 1.65 local star = "*"
                    
                    local display_value = string(`coef', "%9.3f") + "`star'"
                }
                else {
                    local display_value = ""
                }
            }
        }
        else {
            local display_value = ""
        }
        
        if `j' == 1 {
            replace full_sample = "`display_value'" in `i'
        }
        else if `j' == 2 {
            replace quantile100_75 = "`display_value'" in `i'
        }
        else if `j' == 3 {
            replace quantile75_50 = "`display_value'" in `i'
        }
        else if `j' == 4 {
            replace quantile50_25 = "`display_value'" in `i'
        }
        else if `j' == 5 {
            replace quantile25_0 = "`display_value'" in `i'
        }
        else if `j' == 6 {
            replace quantile100_50 = "`display_value'" in `i'
        }
        else if `j' == 7 {
            replace quantile50_0 = "`display_value'" in `i'
        }
    }
}

* Export to Excel
export excel using "output_monthly.xlsx", firstrow(variables) replace

* Display results
list
restore