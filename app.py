from flask import Flask, request, jsonify, render_template, send_file
import numpy as np
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import csv
import io


app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.get_json()

    initial = data['initial']
    spend = data['spend']
    mean = data['mean'] / 100
    stdev = data['stdev'] / 100
    years = data['years']
    trials = data['trials']
    age = data['age']
    workIncome = data['workIncome']
    workUntil = data['workUntil']
    pensionIncome = data['pensionIncome']
    pensionStart = data['pensionStart']
    inflation = data['inflation'] / 100

    np.random.seed(42)
    results = []
    death_maxes = []
    worst_trial = -1
    worst_min_age = 200
    fail_count = 0

    for t in range(trials):
        asset = initial
        assets = []
        min_age_hit = None
        for y in range(years):
            curr_age = age + y
            asset *= (1 + np.random.normal(mean, stdev))
            income = 0
            if curr_age < workUntil:
                income += workIncome
            if curr_age >= pensionStart:
                income += pensionIncome
            asset += income
            asset -= spend * ((1 + inflation) ** y)
            assets.append(asset)
            if asset <= 0 and min_age_hit is None:
                min_age_hit = curr_age
        results.append(assets)
        death_maxes.append(max(assets))
        if min_age_hit:
            fail_count += 1
            if min_age_hit < worst_min_age:
                worst_min_age = min_age_hit
                worst_trial = t

    percentiles = np.percentile(results, [25, 50, 75], axis=0)

    plt.figure(figsize=(10, 6))
    plt.plot(percentiles[0], label="25th percentile")
    plt.plot(percentiles[1], label="50th percentile")
    plt.plot(percentiles[2], label="75th percentile")
    plt.title("Percentile")
    plt.xlabel("Years")
    plt.ylabel("JPY")
    plt.legend()
    plt.grid(True)
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    graph_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return jsonify({
        'failureRate': f"{fail_count / trials * 100:.2f}%",
        'worstTrial': worst_trial,
        'minAge': worst_min_age,
        'deathMax': max(death_maxes),
        'graphBase64': graph_base64
    })

if __name__ == '__main__':
    app.run(debug=True)

from flask import send_file
import csv
import io

@app.route("/simulate_csv", methods=["POST"])
def simulate_csv():
    data = request.get_json()

    initial = float(data["initial"])
    spend = float(data["spend"])
    mean = float(data["mean"]) / 100
    stdev = float(data["stdev"]) / 100
    years = int(data["years"])
    trials = int(data["trials"])
    age = int(data["age"])
    work_income = float(data["workIncome"])
    work_until = int(data["workUntil"])
    pension_income = float(data["pensionIncome"])
    pension_start = int(data["pensionStart"])
    inflation = float(data["inflation"]) / 100

    results = np.zeros((trials, years))

    for t in range(trials):
        assets = initial
        yearly_assets = []
        for y in range(years):
            current_age = age + y
            income = 0
            if current_age < work_until:
                income += work_income
            if current_age >= pension_start:
                income += pension_income

            adjusted_spend = spend * ((1 + inflation) ** y)
            real_return = np.random.normal(mean, stdev)
            assets = (assets - adjusted_spend + income) * (1 + real_return)
            yearly_assets.append(assets if assets > 0 else 0)

        results[t] = yearly_assets

    # CSV生成
    output = io.StringIO()
    writer = csv.writer(output)
    header = ["Year"] + [f"Trial {i+1}" for i in range(trials)]
    writer.writerow(header)

    for year in range(years):
        row = [f"Year {year+1}"] + list(results[:, year])
        writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name="monte_result.csv"
    )

