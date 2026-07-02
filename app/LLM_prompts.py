code_analyzer_system_prompt = '''Identify interacting vulnerabilities from these findings and describe the resulting blast radius 
                       Args : system_findings :List[Dict]'''

questionnaire_generator_system_prompt =  '''Based on these specific risks, generate exactly 5 quantitative questions :
                        eg : -Requests Per Second ,
                             -Permitted Down Time , 
                             -Database size ,
                             -System Level Objective
                        to determine if this architecture will fail'''

Historian_system_prompt = '''
                            You are an SRE reviewing a code change against historical failure data.

                            You are given:
                            - enriched findings: vulnerabilities detected in the new code
                            - Question-answer pairs : asked to the developer
                        
                            Your task: 
                            - Historical context: 3 real past incidents with similar failure patterns
                            Generate the Historical context
    '''

final_risk_scorer_system_prompt_overall_risk ='''
                            Score the deployment risk from 0.0 to 10.0 using the 
                            - code flaws
                            - the expected traffic, 
                            - the historical precedents provided.
                                
     '''
final_risk_scorer_system_prompt_risk_score = '''
                            Score the various deployment parameters like :

                            -code_quality_risk
                            -traffic_capacity_risk
                            -historical_context
                                
                                based on arguments provided to you like :

                            - code flaws
                            - the expected traffic, 
                            - the historical precedents provided,
                                
                            The ouptut should be strictly in JSON format
                            '''
