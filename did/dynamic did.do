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

* Quantile indicators: degree/out_weight_avg/pagerank
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


* Parallel trends test (revised: t=-1 is the base period)
* Manual settings
local y_var "y"          // Specify dependent variable (can be changed to y1-y5)
local group_var "intensity_high6" // Specify grouping variable (choose different quantile groups), intensity_high1 / intensity_high2 / ... or 1 (for full sample)
local pre_periods 12      // Number of pre-treatment periods to test
local post_periods 12     // Number of post-treatment periods to test

* Generate relative time variable
gen rel_time = month - policy_group
replace rel_time = . if missing(policy_group) | policy_group == 0

* Create time dummy variables for event study
forvalues t = -`pre_periods'/`post_periods' {
    if `t' < -1 {  // Multiple pre-treatment periods (t=-4, -3, -2, etc.)
        local t_abs = abs(`t')
        gen pre`t_abs' = (rel_time == `t') * intensity if !missing(rel_time)
    }
    else if `t' == 0 {  // Current period of policy implementation (t=0)
        gen current = (rel_time == 0) * intensity if !missing(rel_time)
    }
    else if `t' > 0 {  // Multiple post-treatment periods (t=1, 2, 3, etc.)
        gen post`t' = (rel_time == `t') * intensity if !missing(rel_time)
    }
    // Note: t=-1 is not generated, serving as the base period
}

* Run event study regression (excluding t=-1 as base period)
reghdfe `y_var' pre* current post* GRP industryStructure urbanLevel populationDestiny techRate fiscalRate ///
    if `group_var' == 1, absorb(id month) vce(cluster id)


estimates store event_study


preserve
clear


set obs `=`pre_periods' + `post_periods' + 1'
gen time = _n - `pre_periods' - 1  // -pre_periods to post_periods


gen coef = .
gen se = .
gen lb = .
gen ub = .

* Fill base period (t=-1)
replace coef = 0 in `=`pre_periods''  // t=-1 is in the middle
replace se = 0 in `=`pre_periods''
replace lb = 0 in `=`pre_periods''
replace ub = 0 in `=`pre_periods''

* Fill pre-treatment periods (t < -1)
forvalues t = `pre_periods'(-1)2 {
    local t_abs = `t' - 1  // Starting from t=-4, corresponding to pre4
    local row = `pre_periods' - `t_abs' + 1
    capture {
        matrix b = e(b)
        matrix V = e(V)
        local coef_val = b[1, "pre`t_abs'"]
        local se_val = sqrt(V["pre`t_abs'", "pre`t_abs'"])
        replace coef = `coef_val' in `row'
        replace se = `se_val' in `row'
        replace lb = `coef_val' - 1.96*`se_val' in `row'
        replace ub = `coef_val' + 1.96*`se_val' in `row'
    }
}

* Fill current period of policy implementation (t=0)
local row = `pre_periods' + 1
capture {
    matrix b = e(b)
    matrix V = e(V)
    local coef_val = b[1, "current"]
    local se_val = sqrt(V["current", "current"])
    replace coef = `coef_val' in `row'
    replace se = `se_val' in `row'
    replace lb = `coef_val' - 1.96*`se_val' in `row'
    replace ub = `coef_val' + 1.96*`se_val' in `row'
}

* Fill post-treatment periods (t > 0)
forvalues t = 1/`post_periods' {
    local row = `pre_periods' + 1 + `t'
    capture {
        matrix b = e(b)
        matrix V = e(V)
        local coef_val = b[1, "post`t'"]
        local se_val = sqrt(V["post`t'", "post`t'"])
        replace coef = `coef_val' in `row'
        replace se = `se_val' in `row'
        replace lb = `coef_val' - 1.96*`se_val' in `row'
        replace ub = `coef_val' + 1.96*`se_val' in `row'
    }
}

* Create zero line
gen zero_line = 0

* Draw parallel trends plot
twoway (rcap lb ub time, lcolor(navy)) ///
       (scatter coef time, mcolor(maroon) msymbol(O) msize(medium)) ///
       (line zero_line time, lpattern(dash) lcolor(gs8)), ///
       xline(-1, lpattern(dash) lcolor(red)) ///
       xtitle("Relative time after policy release", size(medium)) ///
       ytitle("Coefficients", size(vlarg)) ///
       xlabel(-`pre_periods'(1)`post_periods', labsize(*0.75)) ///
	   ylabel(-20(2)10, labsize(*0.75)) ///
       title("Total-Policy Shock-(1)", size(large)) ///
       legend(order(2 "point estimation" 1 "95% confidence interval") rows(2) size(*0.75)) ///
       yscale(range(-20 10))   ///
       graphregion(color(white)) bgcolor(white)
       
graph export "dynamic_results_`y_var'_`group_var'.png", replace width(1200) height(1200)

* Display regression results
estimates replay event_study